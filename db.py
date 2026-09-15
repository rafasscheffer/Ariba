import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from config import settings
from utils import date_sort_key, normalize_version, now_iso, money_fields


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS ariba_order_versions (
    source_key TEXT PRIMARY KEY,
    document_number TEXT NOT NULL,
    buyer_context_anid TEXT,
    po_version REAL,
    payload_id TEXT,
    created_raw TEXT,
    order_date_raw TEXT,
    revision TEXT,
    routing_status TEXT,
    dashboard_status TEXT,
    document_status TEXT,
    customer_name TEXT,
    customer_anid TEXT,
    supplier_name TEXT,
    supplier_anid TEXT,
    vendor_id TEXT,
    company_code TEXT,
    purchasing_org_code TEXT,
    purchasing_group_code TEXT,
    po_amount REAL,
    po_currency TEXT,
    raw_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ariba_document
ON ariba_order_versions(document_number);

CREATE TABLE IF NOT EXISTS sap_orders (
    doc_entry INTEGER PRIMARY KEY,
    doc_num INTEGER,
    num_at_card TEXT,
    card_code TEXT,
    card_name TEXT,
    doc_date TEXT,
    doc_due_date TEXT,
    document_status TEXT,
    cancelled TEXT,
    position_status TEXT,
    raw_json TEXT,
    last_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sap_numatcard
ON sap_orders(num_at_card);

CREATE TABLE IF NOT EXISTS order_monitor (
    document_number TEXT PRIMARY KEY,
    current_po_version REAL,
    ariba_created_raw TEXT,
    ariba_revision TEXT,
    ariba_dashboard_status TEXT,
    sap_found INTEGER NOT NULL DEFAULT 0,
    sap_doc_count INTEGER NOT NULL DEFAULT 0,
    monitor_status TEXT,
    first_seen_monitor_at TEXT,
    last_checked_at TEXT,
    last_event_type TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    document_number TEXT,
    event_type TEXT NOT NULL,
    details_json TEXT
);
"""


class Database:
    def __init__(self):
        settings.ensure_dirs()
        self.path = settings.db_path
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def backup_and_reset(self):
        settings.ensure_dirs()
        if self.path.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = settings.backup_dir / f"monitor_{stamp}.db"
            shutil.copy2(self.path, backup)
        with self.connect() as conn:
            conn.executescript("""
                DELETE FROM event_log;
                DELETE FROM order_monitor;
                DELETE FROM sap_orders;
                DELETE FROM ariba_order_versions;
                DELETE FROM meta;
            """)

    def set_meta(self, key, value):
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO meta(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, str(value)),
            )

    def get_meta(self, key, default=None):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key=?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def log_event(self, document_number, event_type, details=None):
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO event_log(
                    created_at, document_number, event_type, details_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    now_iso(),
                    document_number,
                    event_type,
                    json.dumps(
                        details or {},
                        ensure_ascii=False,
                        default=str,
                    ),
                ),
            )

    def upsert_ariba_order(self, source_key, order, buyer_anid):
        now = now_iso()
        doc = str(order.get("documentNumber") or "").strip()
        if not doc:
            return None

        amount, currency = money_fields(order.get("poAmount"))
        raw = json.dumps(order, ensure_ascii=False, default=str)

        with self.connect() as conn:
            any_doc = conn.execute(
                """
                SELECT 1 FROM ariba_order_versions
                WHERE document_number=?
                LIMIT 1
                """,
                (doc,),
            ).fetchone()

            existing = conn.execute(
                """
                SELECT 1 FROM ariba_order_versions
                WHERE source_key=?
                """,
                (source_key,),
            ).fetchone()

            conn.execute(
                """
                INSERT INTO ariba_order_versions(
                    source_key, document_number, buyer_context_anid,
                    po_version, payload_id, created_raw, order_date_raw,
                    revision, routing_status, dashboard_status,
                    document_status, customer_name, customer_anid,
                    supplier_name, supplier_anid, vendor_id,
                    company_code, purchasing_org_code,
                    purchasing_group_code, po_amount, po_currency,
                    raw_json, first_seen_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    revision=excluded.revision,
                    routing_status=excluded.routing_status,
                    dashboard_status=excluded.dashboard_status,
                    document_status=excluded.document_status,
                    customer_name=excluded.customer_name,
                    customer_anid=excluded.customer_anid,
                    supplier_name=excluded.supplier_name,
                    supplier_anid=excluded.supplier_anid,
                    vendor_id=excluded.vendor_id,
                    company_code=excluded.company_code,
                    purchasing_org_code=excluded.purchasing_org_code,
                    purchasing_group_code=excluded.purchasing_group_code,
                    po_amount=excluded.po_amount,
                    po_currency=excluded.po_currency,
                    raw_json=excluded.raw_json,
                    last_seen_at=excluded.last_seen_at
                """,
                (
                    source_key, doc, buyer_anid,
                    order.get("poVersion"),
                    order.get("payloadId"),
                    order.get("created"),
                    order.get("orderDate"),
                    order.get("revision"),
                    order.get("status"),
                    order.get("dashboardStatus"),
                    order.get("documentStatus"),
                    order.get("customerName"),
                    order.get("customerANID"),
                    order.get("supplierName"),
                    order.get("supplierANID"),
                    order.get("vendorId"),
                    order.get("companyCode"),
                    order.get("purchasingOrgCode"),
                    order.get("purchasingGroupCode"),
                    amount, currency, raw,
                    now if not existing else now,
                    now,
                ),
            )

        if existing:
            return {"event": None, "document_number": doc}
        return {
            "event": "NEW_VERSION" if any_doc else "NEW_ORDER",
            "document_number": doc,
        }

    def latest_documents(self):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ariba_order_versions"
            ).fetchall()

        grouped = {}
        for row in rows:
            item = dict(row)
            doc = item["document_number"]
            current = grouped.get(doc)
            if current is None:
                grouped[doc] = item
                continue

            cur_key = (
                normalize_version(current.get("po_version")),
                date_sort_key(current.get("created_raw")),
            )
            new_key = (
                normalize_version(item.get("po_version")),
                date_sort_key(item.get("created_raw")),
            )
            if new_key > cur_key:
                grouped[doc] = item

        return sorted(
            grouped.values(),
            key=lambda x: date_sort_key(x.get("created_raw")),
            reverse=True,
        )

    def latest_ariba_for_document(self, document_number):
        rows = [
            x for x in self.latest_documents()
            if x["document_number"] == document_number
        ]
        return rows[0] if rows else None

    def upsert_sap_orders(self, num_at_card, orders):
        now = now_iso()
        with self.connect() as conn:
            for order in orders:
                conn.execute(
                    """
                    INSERT INTO sap_orders(
                        doc_entry, doc_num, num_at_card, card_code,
                        card_name, doc_date, doc_due_date,
                        document_status, cancelled, position_status,
                        raw_json, last_seen_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(doc_entry) DO UPDATE SET
                        doc_num=excluded.doc_num,
                        num_at_card=excluded.num_at_card,
                        card_code=excluded.card_code,
                        card_name=excluded.card_name,
                        doc_date=excluded.doc_date,
                        doc_due_date=excluded.doc_due_date,
                        document_status=excluded.document_status,
                        cancelled=excluded.cancelled,
                        position_status=excluded.position_status,
                        raw_json=excluded.raw_json,
                        last_seen_at=excluded.last_seen_at
                    """,
                    (
                        order.get("DocEntry"),
                        order.get("DocNum"),
                        order.get("NumAtCard") or num_at_card,
                        order.get("CardCode"),
                        order.get("CardName"),
                        order.get("DocDate"),
                        order.get("DocDueDate"),
                        order.get("DocumentStatus"),
                        order.get("Cancelled"),
                        order.get("U_S7T_PosicaoPed"),
                        json.dumps(
                            order,
                            ensure_ascii=False,
                            default=str,
                        ),
                        now,
                    ),
                )

    def sap_for_document(self, document_number):
        with self.connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT * FROM sap_orders
                    WHERE num_at_card=?
                    ORDER BY doc_num
                    """,
                    (document_number,),
                ).fetchall()
            ]

    def upsert_monitor(
        self,
        document_number,
        latest_ariba,
        sap_found,
        sap_doc_count,
        monitor_status,
        event_type=None,
    ):
        now = now_iso()
        with self.connect() as conn:
            existing = conn.execute(
                """
                SELECT first_seen_monitor_at
                FROM order_monitor
                WHERE document_number=?
                """,
                (document_number,),
            ).fetchone()
            first_seen = (
                existing["first_seen_monitor_at"]
                if existing else now
            )

            conn.execute(
                """
                INSERT INTO order_monitor(
                    document_number, current_po_version,
                    ariba_created_raw, ariba_revision,
                    ariba_dashboard_status, sap_found,
                    sap_doc_count, monitor_status,
                    first_seen_monitor_at, last_checked_at,
                    last_event_type, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_number) DO UPDATE SET
                    current_po_version=excluded.current_po_version,
                    ariba_created_raw=excluded.ariba_created_raw,
                    ariba_revision=excluded.ariba_revision,
                    ariba_dashboard_status=excluded.ariba_dashboard_status,
                    sap_found=excluded.sap_found,
                    sap_doc_count=excluded.sap_doc_count,
                    monitor_status=excluded.monitor_status,
                    last_checked_at=excluded.last_checked_at,
                    last_event_type=COALESCE(
                        excluded.last_event_type,
                        order_monitor.last_event_type
                    ),
                    updated_at=excluded.updated_at
                """,
                (
                    document_number,
                    latest_ariba.get("po_version"),
                    latest_ariba.get("created_raw"),
                    latest_ariba.get("revision"),
                    latest_ariba.get("dashboard_status"),
                    1 if sap_found else 0,
                    sap_doc_count,
                    monitor_status,
                    first_seen,
                    now,
                    event_type,
                    now,
                ),
            )

    def monitor_rows(self):
        with self.connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT * FROM order_monitor
                    ORDER BY ariba_created_raw DESC, document_number DESC
                    """
                ).fetchall()
            ]

    def followup_documents(self):
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT document_number
                FROM order_monitor
                WHERE monitor_status <> 'ENCERRADO'
                """
            ).fetchall()
        return [r["document_number"] for r in rows]

    def counts(self):
        with self.connect() as conn:
            versions = conn.execute(
                "SELECT COUNT(*) n FROM ariba_order_versions"
            ).fetchone()["n"]
            unique_docs = conn.execute(
                """
                SELECT COUNT(DISTINCT document_number) n
                FROM ariba_order_versions
                """
            ).fetchone()["n"]
            audited = conn.execute(
                "SELECT COUNT(*) n FROM order_monitor"
            ).fetchone()["n"]
        return {
            "versions": versions,
            "unique_docs": unique_docs,
            "audited": audited,
        }

    def all_ariba_versions(self):
        with self.connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT * FROM ariba_order_versions
                    ORDER BY created_raw DESC
                    """
                ).fetchall()
            ]
