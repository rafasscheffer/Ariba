import json
import requests
import urllib3

from config import settings


if not settings.sap_verify_ssl:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


NUM_AT_CARD = "4502477221"


def main():
    session = requests.Session()

    print("Login SAP...")

    login = session.post(
        f"{settings.sap_url}/b1s/v1/Login",
        json={
            "CompanyDB": settings.sap_company_db,
            "UserName": settings.sap_user,
            "Password": settings.sap_password,
        },
        verify=settings.sap_verify_ssl,
        timeout=30,
    )

    print("HTTP Login:", login.status_code)

    if login.status_code != 200:
        print(login.text)
        return

    print()
    print("Consultando pedido:", NUM_AT_CARD)

    response = session.get(
        f"{settings.sap_url}/b1s/v1/Orders",
        params={"$filter": f"NumAtCard eq '{NUM_AT_CARD}'"},
        verify=settings.sap_verify_ssl,
        timeout=30,
    )

    print("HTTP Consulta:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return

    pedidos = response.json().get("value", [])

    if not pedidos:
        print("Pedido nao encontrado.")
        return

    for pedido in pedidos:
        print()
        print("=" * 70)
        print("DocNum:", pedido.get("DocNum"))
        print("NumAtCard:", pedido.get("NumAtCard"))
        print("=" * 70)

        print()
        print("CAMPO QUE ESTAVAMOS USANDO:")
        print("U_S7T_PosicaoPed =", repr(pedido.get("U_S7T_PosicaoPed")))

        print()
        print("CAMPOS POSSIVELMENTE RELACIONADOS:")
        print("-" * 70)

        for campo, valor in sorted(pedido.items()):
            nome = campo.upper()

            if any(
                termo in nome
                for termo in [
                    "POS",
                    "STATUS",
                    "S7T",
                    "FAT",
                    "PED",
                ]
            ):
                print(f"{campo:<45} = {repr(valor)}")

        print()
        print("TODOS OS UDFs DO PEDIDO:")
        print("-" * 70)

        for campo, valor in sorted(pedido.items()):
            if campo.upper().startswith("U_"):
                print(f"{campo:<45} = {repr(valor)}")

        with open(
            f"diagnostico_{NUM_AT_CARD}.json",
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                pedido,
                arquivo,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        print()
        print(f"JSON completo salvo em diagnostico_{NUM_AT_CARD}.json")

    try:
        session.post(
            f"{settings.sap_url}/b1s/v1/Logout",
            verify=settings.sap_verify_ssl,
            timeout=10,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
