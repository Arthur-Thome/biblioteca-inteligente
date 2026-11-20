"""Mantém o servidor Flask sob controle gracioso dos scripts locais."""

from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / "runtime" / "flask-process.json"
sys.path.insert(0, str(ROOT))

from backend import create_app


def main() -> int:
    """Executa o servidor local e atende solicitação de parada por evento Windows.

    O evento é nomeado com o PID do processo para que o script de parada alcance
    somente esta instância. O servidor Werkzeug é encerrado por ``shutdown()``.
    """
    if os.name != "nt":
        print("Este gerenciador de processo foi preparado para Windows.")
        return 2
    runtime_dir = ROOT / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    server = make_server("127.0.0.1", 5000, create_app(), threaded=True)
    pid = os.getpid()
    event_name = rf"Local\BibliotecaInteligenteFlaskStop_{pid}"
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateEventW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_wchar_p,
    ]
    kernel.CreateEventW.restype = ctypes.c_void_p
    event = kernel.CreateEventW(None, True, False, event_name)
    if not event:
        server.server_close()
        raise ctypes.WinError(ctypes.get_last_error())
    PID_FILE.write_text(
        json.dumps(
            {
                "pid": pid,
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "python_executable": str(Path(sys.executable)),
                "project_root": str(ROOT.resolve()),
                "event_name": event_name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    def wait_for_stop() -> None:
        """Aguarda evento local e pede ao servidor que termine com segurança."""
        wait = kernel.WaitForSingleObject
        wait.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        wait.restype = ctypes.c_uint32
        if wait(event, 0xFFFFFFFF) == 0:
            server.shutdown()

    listener = threading.Thread(target=wait_for_stop, daemon=True)
    listener.start()
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        kernel.CloseHandle(ctypes.c_void_p(event))
        try:
            record = json.loads(PID_FILE.read_text(encoding="utf-8"))
            if record.get("pid") == pid:
                PID_FILE.unlink()
        except (OSError, ValueError):
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
