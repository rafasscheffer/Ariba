import logging
import time
from datetime import timedelta
import requests
from config import settings

log = logging.getLogger(__name__)


class AribaClient:
    def __init__(self):
        self.session = requests.Session()
        self.token = None

    def authenticate(self):
        response = self.session.post(
            settings.ariba_token_url,
            headers={
                "Authorization": f"Basic {settings.ariba_basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"OAuth Ariba HTTP {response.status_code}: {response.text}"
            )
        self.token = response.json().get("access_token")
        if not self.token:
            raise RuntimeError("OAuth Ariba sem access_token.")
        log.info("OAuth Ariba concluido.")

    def _headers(self):
        if not self.token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self.token}",
            "apikey": settings.ariba_app_key,
            "X-ARIBA-NETWORK-ID": settings.ariba_supplier_anid,
            "Accept": "application/json",
        }

    def _get(self, path, params):
        url = f"{settings.ariba_api_base.rstrip('/')}/{path.lstrip('/')}"
        response = self.session.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=60,
        )
        if response.status_code == 401:
            self.authenticate()
            response = self.session.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=60,
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Ariba HTTP {response.status_code}: {response.text}"
            )
        return response.json()

    def fetch_orders_window(self, buyer_anid, start_dt, end_dt):
        filtro = (
            f"buyerANID eq {buyer_anid} "
            f"and startDate eq {start_dt.strftime('%Y-%m-%dT%H:%M:%S')} "
            f"and endDate eq {end_dt.strftime('%Y-%m-%dT%H:%M:%S')}"
        )

        rows_all = []
        skip = 0
        top = 100

        while True:
            data = self._get(
                "orders",
                {
                    "$filter": filtro,
                    "$top": top,
                    "$skip": skip,
                },
            )
            rows = data.get("content", [])
            rows_all.extend(rows)

            log.info(
                "Ariba %s | %s -> %s | skip=%s | %s registros",
                buyer_anid,
                start_dt,
                end_dt,
                skip,
                len(rows),
            )

            if not rows:
                break
            if data.get("lastPage") is True:
                break
            if len(rows) < top:
                break

            skip += len(rows)
            time.sleep(0.10)

        return rows_all

    def fetch_period(self, buyer_anid, start_dt, end_dt):
        cursor = start_dt
        while cursor < end_dt:
            chunk_end = min(cursor + timedelta(days=30), end_dt)
            rows = self.fetch_orders_window(
                buyer_anid,
                cursor,
                chunk_end,
            )
            yield cursor, chunk_end, rows
            cursor = chunk_end
