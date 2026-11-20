"""Envia evento de parada somente à instância Flask indicada pelo PID."""

from __future__ import annotations

import ctypes
import sys


def main() -> int:
    """Sinaliza o evento Windows do gerenciador Flask verificado pelo PowerShell."""
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("O PID da aplicação não foi informado corretamente.")
        return 2
    pid = int(sys.argv[1])
    name = f"Local\\BibliotecaInteligenteFlaskStop_{pid}"
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenEventW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
    kernel.OpenEventW.restype = ctypes.c_void_p
    event = kernel.OpenEventW(0x0002, False, name)
    if not event:
        print("O evento de parada do servidor do projeto não está disponível.")
        return 1
    try:
        if not kernel.SetEvent(ctypes.c_void_p(event)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(ctypes.c_void_p(event))
    print("O encerramento gracioso do servidor Flask foi solicitado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
