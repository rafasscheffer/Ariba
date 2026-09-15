import os
import sys
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


def runtime_dir():
    """
    No VS Code/Python, usa a pasta do projeto.
    No PyInstaller --onefile, usa a pasta onde o EXE esta instalado.
    Isso evita procurar .env/data/reports dentro da pasta temporaria _MEI...
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = runtime_dir()
ENV_PATH = BASE_DIR / ".env"

# utf-8-sig aceita .env normal e tambem .env salvo com BOM pelo Windows.
load_dotenv(dotenv_path=ENV_PATH, encoding="utf-8-sig")


def _bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _int(name, default):
    raw = os.getenv(name)
    return int(raw) if raw else default


def _float(name, default):
    raw = os.getenv(name)
    return float(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    base_dir: Path = BASE_DIR
    env_path: Path = ENV_PATH
    data_dir: Path = BASE_DIR / "data"
    logs_dir: Path = BASE_DIR / "logs"
    reports_dir: Path = BASE_DIR / "reports"
    backup_dir: Path = BASE_DIR / "data" / "backups"

    ariba_app_key: str = os.getenv("ARIBA_APP_KEY", "")
    ariba_basic_auth: str = os.getenv("ARIBA_BASIC_AUTH", "")
    ariba_supplier_anid: str = os.getenv("ARIBA_SUPPLIER_ANID", "")
    ariba_buyer_anids_raw: str = os.getenv("ARIBA_BUYER_ANIDS", "")
    ariba_token_url: str = os.getenv(
        "ARIBA_TOKEN_URL",
        "https://api.ariba.com/v2/oauth/token",
    )
    ariba_api_base: str = os.getenv(
        "ARIBA_API_BASE",
        "https://openapi.ariba.com/api/purchase-orders-supplier/v1/prod",
    )
    ariba_initial_days: int = _int("ARIBA_INITIAL_DAYS", 90)
    ariba_incremental_lookback_days: int = _int(
        "ARIBA_INCREMENTAL_LOOKBACK_DAYS", 7
    )

    sap_url: str = os.getenv("SAP_SL_URL", "").rstrip("/")
    sap_company_db: str = os.getenv("SAP_COMPANY_DB", "")
    sap_user: str = os.getenv("SAP_USER", "")
    sap_password: str = os.getenv("SAP_PASSWORD", "")
    sap_verify_ssl: bool = _bool("SAP_VERIFY_SSL", False)
    sap_reconcile_delay_seconds: float = _float(
        "SAP_RECONCILE_DELAY_SECONDS", 0.05
    )

    notify_ariba_changes: bool = _bool("NOTIFY_ARIBA_CHANGES", True)
    final_sap_positions_raw: str = os.getenv(
        "FINAL_SAP_POSITIONS", "FATURADO,EXPEDIDO,CANCELADO"
    )

    @property
    def ariba_buyer_anids(self):
        return [
            x.strip()
            for x in self.ariba_buyer_anids_raw.split(",")
            if x.strip()
        ]

    @property
    def final_sap_positions(self):
        return {
            x.strip().upper()
            for x in self.final_sap_positions_raw.split(",")
            if x.strip()
        }

    @property
    def db_path(self):
        return self.data_dir / "monitor.db"

    def ensure_dirs(self):
        for path in [
            self.data_dir,
            self.logs_dir,
            self.reports_dir,
            self.backup_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def validate(self):
        required = {
            "ARIBA_APP_KEY": self.ariba_app_key,
            "ARIBA_BASIC_AUTH": self.ariba_basic_auth,
            "ARIBA_SUPPLIER_ANID": self.ariba_supplier_anid,
            "ARIBA_BUYER_ANIDS": self.ariba_buyer_anids_raw,
            "SAP_SL_URL": self.sap_url,
            "SAP_COMPANY_DB": self.sap_company_db,
            "SAP_USER": self.sap_user,
            "SAP_PASSWORD": self.sap_password,
        }
        placeholders = ("COLE_", "SEU_", "SUA_")
        missing = [
            k for k, v in required.items()
            if not v or str(v).startswith(placeholders)
        ]
        if missing:
            raise RuntimeError(
                "Configure o arquivo .env. Pendencias: "
                + ", ".join(missing)
                + f" | Caminho procurado: {self.env_path}"
            )


settings = Settings()
