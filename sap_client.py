import logging
import requests
import urllib3
from config import settings

log = logging.getLogger(__name__)

if not settings.sap_verify_ssl:
    urllib3.disable_warnings(
        urllib3.exceptions.InsecureRequestWarning
    )


class SAPClient:
    def __init__(self):
        self.session = requests.Session()
        self.logged_in = False

    def login(self):
        response = self.session.post(
            f"{settings.sap_url}/b1s/v1/Login",
            json={
                "CompanyDB": settings.sap_company_db,
                "UserName": settings.sap_user,
                "Password": settings.sap_password,
            },
            verify=settings.sap_verify_ssl,
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Login SAP HTTP {response.status_code}: {response.text}"
            )
        self.logged_in = True
        log.info("Login SAP Service Layer concluido.")

    def logout(self):
        if not self.logged_in:
            return
        try:
            self.session.post(
                f"{settings.sap_url}/b1s/v1/Logout",
                verify=settings.sap_verify_ssl,
                timeout=10,
            )
        finally:
            self.logged_in = False

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.logout()

    @staticmethod
    def _escape(value):
        return str(value).replace("'", "''")

    def orders_by_num_at_card(self, num_at_card):
        safe = self._escape(num_at_card)
        response = self.session.get(
            f"{settings.sap_url}/b1s/v1/Orders",
            params={
                "$select": (
                    "DocEntry,DocNum,NumAtCard,CardCode,CardName,"
                    "DocDate,DocDueDate,DocumentStatus,Cancelled,"
                    "U_S7T_PosicaoPed"
                ),
                "$filter": f"NumAtCard eq '{safe}'",
                "$orderby": "DocNum",
            },
            verify=settings.sap_verify_ssl,
            timeout=30,
        )
        if response.status_code == 401:
            self.login()
            return self.orders_by_num_at_card(num_at_card)
        if response.status_code != 200:
            raise RuntimeError(
                f"Consulta SAP HTTP {response.status_code}: {response.text}"
            )
        return response.json().get("value", [])
