import argparse
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta

from ariba_client import AribaClient
from config import settings
from db import Database
from logging_setup import setup_logging
from notifier import notify
from reporting import export_all
from sap_client import SAPClient
from status_logic import classify, reasons
from utils import ariba_source_key, now_iso


log = logging.getLogger(__name__)


def ingest(db, ariba, start_dt, end_dt, emit_events):
    events = defaultdict(list)
    total = 0

    for buyer_anid in settings.ariba_buyer_anids:
        for chunk_start, chunk_end, rows in ariba.fetch_period(
            buyer_anid,
            start_dt,
            end_dt,
        ):
            print(
                f"Ariba {buyer_anid}: "
                f"{chunk_start:%d/%m/%Y} -> {chunk_end:%d/%m/%Y} "
                f"| {len(rows)} registros"
            )
            total += len(rows)

            for order in rows:
                key = ariba_source_key(order, buyer_anid)
                result = db.upsert_ariba_order(
                    key,
                    order,
                    buyer_anid,
                )
                if emit_events and result and result.get("event"):
                    doc = result["document_number"]
                    events[doc].append(result["event"])
                    db.log_event(
                        doc,
                        f"ARIBA_{result['event']}",
                        {"buyerANID": buyer_anid},
                    )

    return total, events


def test_connections():
    settings.validate()
    ariba = AribaClient()
    ariba.authenticate()
    print("ARIBA: OK")

    with SAPClient():
        print("SAP SERVICE LAYER: OK")


def validate_initial_90_days():
    settings.validate()
    db = Database()

    print()
    print("=" * 72)
    print("VALIDACAO INICIAL - ARIBA x SAP")
    print("=" * 72)
    print(f"Periodo: ultimos {settings.ariba_initial_days} dias")
    print("O banco atual sera salvo em backup antes da nova validacao.")
    print()

    db.backup_and_reset()

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=settings.ariba_initial_days)

    db.set_meta(
        "validation_period_start",
        start_dt.strftime("%d/%m/%Y %H:%M"),
    )
    db.set_meta(
        "validation_period_end",
        end_dt.strftime("%d/%m/%Y %H:%M"),
    )
    db.set_meta(
        "validation_days",
        settings.ariba_initial_days,
    )

    ariba = AribaClient()
    ariba.authenticate()

    print("1/2 - Importando historico do Ariba...")
    total_received, _ = ingest(
        db,
        ariba,
        start_dt,
        end_dt,
        emit_events=False,
    )

    docs = db.latest_documents()
    print()
    print(
        f"Ariba: {total_received} registros/versoes recebidos; "
        f"{len(docs)} pedidos unicos."
    )
    print()
    print("2/2 - Conferindo TODOS os pedidos no SAP B1...")
    print()

    no_sap = 0
    followup = 0
    closed = 0

    with SAPClient() as sap:
        for idx, latest in enumerate(docs, start=1):
            doc = latest["document_number"]
            orders = sap.orders_by_num_at_card(doc)
            db.upsert_sap_orders(doc, orders)

            status = classify(orders)
            db.upsert_monitor(
                document_number=doc,
                latest_ariba=latest,
                sap_found=bool(orders),
                sap_doc_count=len(orders),
                monitor_status=status,
                event_type="INITIAL_90D_VALIDATION",
            )

            if status == "SEM_SAP":
                no_sap += 1
            elif status == "ENCERRADO":
                closed += 1
            else:
                followup += 1

            db.log_event(
                doc,
                "INITIAL_90D_VALIDATION",
                {
                    "status": status,
                    "docnums": [x.get("DocNum") for x in orders],
                    "reasons": reasons(orders),
                },
            )

            if settings.sap_reconcile_delay_seconds > 0 and idx < len(docs):
                time.sleep(settings.sap_reconcile_delay_seconds)

            if idx % 25 == 0 or idx == len(docs):
                print(
                    f"Conferidos {idx}/{len(docs)} | "
                    f"Encerrados: {closed} | "
                    f"Em acompanhamento: {followup} | "
                    f"Sem SAP: {no_sap}"
                )

    db.set_meta(
        "full_reconciliation_completed_at",
        now_iso(),
    )
    db.set_meta(
        "full_reconciliation_count",
        len(docs),
    )

    files = export_all(db)

    print()
    print("=" * 72)
    print("VALIDACAO CONCLUIDA")
    print("=" * 72)
    print(f"Pedidos unicos conferidos: {len(docs)}")
    print(f"Encerrados FATURADO/EXPEDIDO/CANCELADO: {closed}")
    print(f"Em acompanhamento: {followup}")
    print(f"Novos / sem SAP: {no_sap}")
    print()
    print(f"Painel: {files['html']}")
    print(f"Auditoria completa: {files['audit']}")
    print(f"Pendencias: {files['open']}")
    print(f"Resumo TXT: {files['summary']}")


def run_monitor():
    settings.validate()
    db = Database()

    if not db.get_meta("full_reconciliation_completed_at"):
        raise RuntimeError(
            "A validacao inicial ainda nao foi concluida. "
            "Execute validar_90_dias.bat primeiro."
        )

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=settings.ariba_incremental_lookback_days)

    ariba = AribaClient()
    ariba.authenticate()

    _, events = ingest(
        db,
        ariba,
        start_dt,
        end_dt,
        emit_events=True,
    )

    docs_to_check = set(events.keys())
    docs_to_check.update(db.followup_documents())

    new_without_sap = []
    changed_existing = []

    if docs_to_check:
        with SAPClient() as sap:
            for doc in sorted(docs_to_check):
                latest = db.latest_ariba_for_document(doc)
                if not latest:
                    continue

                orders = sap.orders_by_num_at_card(doc)
                db.upsert_sap_orders(doc, orders)

                status = classify(orders)
                event_list = events.get(doc, [])
                event_type = (
                    "NEW_VERSION"
                    if "NEW_VERSION" in event_list
                    else "NEW_ORDER"
                    if "NEW_ORDER" in event_list
                    else None
                )

                db.upsert_monitor(
                    document_number=doc,
                    latest_ariba=latest,
                    sap_found=bool(orders),
                    sap_doc_count=len(orders),
                    monitor_status=status,
                    event_type=event_type,
                )

                if event_type == "NEW_ORDER" and not orders:
                    new_without_sap.append(doc)

                if (
                    event_type == "NEW_VERSION"
                    and orders
                    and settings.notify_ariba_changes
                ):
                    changed_existing.append(doc)

    files = export_all(db)
    db.set_meta("last_successful_run", now_iso())

    if new_without_sap:
        notify(
            "Novos pedidos Ariba",
            f"{len(new_without_sap)} pedido(s) ainda sem SAP: "
            + ", ".join(new_without_sap[:8]),
        )

    if changed_existing:
        notify(
            "Pedidos Ariba alterados",
            f"{len(changed_existing)} pedido(s) com nova versao: "
            + ", ".join(changed_existing[:8]),
        )

    # Se houve pedido novo ou nova versao no Ariba,
    # abre automaticamente o painel no navegador.
    if events:
        try:
            os.startfile(str(files["html"]))
        except Exception as exc:
            log.warning(
                "Nao foi possivel abrir o painel automaticamente: %s",
                exc,
            )

    audit_count = db.counts()["audited"]
    open_count = len(db.followup_documents())

    print()
    print("=" * 72)
    print("MONITOR ATUALIZADO")
    print("=" * 72)
    print(f"Pedidos auditados na base: {audit_count}")
    print(f"Pedidos que exigem acompanhamento: {open_count}")
    print(f"Novos sem SAP nesta execucao: {len(new_without_sap)}")
    print(f"Revisoes Ariba detectadas: {len(changed_existing)}")
    print(f"Painel: {files['html']}")


def status():
    db = Database()
    files = export_all(db)
    counts = db.counts()

    print()
    print("=" * 72)
    print("STATUS DO MONITOR")
    print("=" * 72)
    print(
        "Periodo validado: "
        f"{db.get_meta('validation_period_start', '-')} ate "
        f"{db.get_meta('validation_period_end', '-')}"
    )
    print(
        "Validacao SAP concluida em: "
        f"{db.get_meta('full_reconciliation_completed_at', 'NAO')}"
    )
    print(f"Registros/versoes Ariba: {counts['versions']}")
    print(f"Pedidos Ariba unicos: {counts['unique_docs']}")
    print(f"Pedidos conferidos no SAP: {counts['audited']}")
    print(f"Em acompanhamento: {len(db.followup_documents())}")
    print(f"Painel: {files['html']}")


def main():
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["test", "validate90", "run", "status"],
    )
    args = parser.parse_args()

    try:
        if args.command == "test":
            test_connections()
        elif args.command == "validate90":
            validate_initial_90_days()
        elif args.command == "run":
            run_monitor()
        elif args.command == "status":
            status()
    except Exception as exc:
        log.exception("Falha: %s", exc)
        print()
        print("ERRO:")
        print(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
