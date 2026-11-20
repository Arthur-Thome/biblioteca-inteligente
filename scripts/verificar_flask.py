"""Confere a saúde HTTP local sem imprimir tracebacks de conexão recusada."""

from __future__ import annotations

import requests


def main() -> int:
    """Classifica Flask como respondendo, parado ou indisponível.

    Retorno:
        Zero para HTTP 200, dois para servidor parado e um para HTTP inesperado.

    Tratamento de erros:
        Falhas de conexão e timeout são resumidos sem expor traceback interno.
    """
    try:
        response = requests.get("http://127.0.0.1:5000/api/health", timeout=3)
    except requests.ConnectionError:
        print("Servidor Flask parado")
        return 2
    except requests.Timeout:
        print("Servidor Flask sem resposta no prazo")
        return 1
    except requests.RequestException as error:
        print(f"Verificação Flask falhou: {type(error).__name__}")
        return 1
    if response.status_code != 200:
        print(f"Servidor Flask respondeu HTTP {response.status_code}")
        return 1
    print("Servidor Flask respondendo HTTP 200")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
