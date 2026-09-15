import csv
import html
from collections import Counter
from datetime import datetime
from config import settings
from status_logic import reasons, sap_position
from utils import local_now_text


def _join_unique(values):
    out = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return " | ".join(out)


def _audit_rows(db):
    rows = []
    for monitor in db.monitor_rows():
        doc = monitor["document_number"]
        sap = db.sap_for_document(doc)

        positions = [sap_position(x) for x in sap]
        followup = monitor["monitor_status"] != "ENCERRADO"

        rows.append({
            "Pedido Ariba": doc,
            "Versao Ariba": monitor.get("current_po_version"),
            "Data Ariba": monitor.get("ariba_created_raw"),
            "Encontrado SAP": "SIM" if sap else "NAO",
            "Qtd DocNum": len(sap),
            "DocNum": _join_unique(x.get("doc_num") for x in sap),
            "CardCode": _join_unique(x.get("card_code") for x in sap),
            "Cliente": _join_unique(x.get("card_name") for x in sap),
            "Posicao SAP": _join_unique(positions),
            "Encerrado": "NAO" if followup else "SIM",
            "Motivo acompanhamento": _join_unique(reasons(sap)) if followup else "",
            "Ultima verificacao": monitor.get("last_checked_at"),
        })
    return rows


def _write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=columns,
            extrasaction="ignore",
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)


def export_audit_csv(db):
    path = settings.reports_dir / "auditoria_90_dias.csv"
    rows = _audit_rows(db)
    columns = [
        "Pedido Ariba",
        "Versao Ariba",
        "Data Ariba",
        "Encontrado SAP",
        "Qtd DocNum",
        "DocNum",
        "CardCode",
        "Cliente",
        "Posicao SAP",
        "Encerrado",
        "Motivo acompanhamento",
        "Ultima verificacao",
    ]
    _write_csv(path, rows, columns)
    return path


def export_open_csv(db):
    path = settings.reports_dir / "pedidos_em_acompanhamento.csv"
    rows = [
        row for row in _audit_rows(db)
        if row["Encerrado"] == "NAO"
    ]
    columns = [
        "Pedido Ariba",
        "Versao Ariba",
        "Data Ariba",
        "Encontrado SAP",
        "Qtd DocNum",
        "DocNum",
        "CardCode",
        "Cliente",
        "Posicao SAP",
        "Motivo acompanhamento",
        "Ultima verificacao",
    ]
    _write_csv(path, rows, columns)
    return path


def export_ariba_versions_csv(db):
    path = settings.reports_dir / "historico_ariba_90_dias.csv"
    rows = db.all_ariba_versions()

    columns = [
        "document_number",
        "buyer_context_anid",
        "po_version",
        "payload_id",
        "created_raw",
        "order_date_raw",
        "revision",
        "routing_status",
        "dashboard_status",
        "document_status",
        "customer_name",
        "customer_anid",
        "supplier_name",
        "supplier_anid",
        "vendor_id",
        "company_code",
        "purchasing_org_code",
        "purchasing_group_code",
        "po_amount",
        "po_currency",
        "first_seen_at",
        "last_seen_at",
    ]
    _write_csv(path, rows, columns)
    return path


def export_summary_txt(db):
    path = settings.reports_dir / "resumo_validacao.txt"
    audit = _audit_rows(db)
    open_rows = [x for x in audit if x["Encerrado"] == "NAO"]
    no_sap = [x for x in open_rows if x["Encontrado SAP"] == "NAO"]
    closed = [x for x in audit if x["Encerrado"] == "SIM"]

    positions = Counter()
    for row in open_rows:
        raw = row["Motivo acompanhamento"]
        for item in [x.strip() for x in raw.split("|") if x.strip()]:
            positions[item] += 1

    lines = [
        "MONITOR ARIBA x SAP BUSINESS ONE - RESUMO DE VALIDACAO",
        "=" * 64,
        f"Gerado em: {local_now_text()}",
        f"Periodo inicial: {db.get_meta('validation_period_start', '-')}",
        f"Ate: {db.get_meta('validation_period_end', '-')}",
        f"Validacao SAP concluida em: {db.get_meta('full_reconciliation_completed_at', '-')}",
        "",
        f"Pedidos Ariba unicos conferidos no SAP: {len(audit)}",
        f"Encerrados (todos DocNum FATURADO/EXPEDIDO/CANCELADO): {len(closed)}",
        f"Exigem acompanhamento: {len(open_rows)}",
        f"Novos / nao localizados no SAP: {len(no_sap)}",
        "",
        "STATUS QUE EXIGEM ACOMPANHAMENTO:",
    ]
    if positions:
        for key, count in sorted(positions.items()):
            lines.append(f"- {key}: {count}")
    else:
        lines.append("- Nenhum")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def export_html(db):
    path = settings.reports_dir / "painel.html"
    audit = _audit_rows(db)
    open_rows = [x for x in audit if x["Encerrado"] == "NAO"]
    closed_rows = [x for x in audit if x["Encerrado"] == "SIM"]
    new_rows = [
        x for x in open_rows
        if x["Encontrado SAP"] == "NAO"
    ]

    pos_counts = Counter()
    for row in open_rows:
        for item in [
            x.strip()
            for x in row["Motivo acompanhamento"].split("|")
            if x.strip()
        ]:
            if item != "NOVO / NAO LOCALIZADO NO SAP":
                pos_counts[item] += 1

    cards = [
        ("Pedidos conferidos", len(audit), "blue"),
        ("Encerrados", len(closed_rows), "green"),
        ("Em acompanhamento", len(open_rows), "orange"),
        ("Novos / sem SAP", len(new_rows), "red"),
    ]

    for pos, count in sorted(
        pos_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        cards.append((pos, count, "gray"))

    cards_html = "".join(
        f"""
        <div class="card {css}">
          <div class="card-number">{count}</div>
          <div class="card-label">{html.escape(label)}</div>
        </div>
        """
        for label, count, css in cards
    )

    validation_done = db.get_meta(
        "full_reconciliation_completed_at", ""
    )
    validation_class = "ok" if validation_done else "warn"
    validation_text = (
        "VALIDACAO COMPLETA CONCLUIDA"
        if validation_done
        else "VALIDACAO COMPLETA AINDA NAO CONCLUIDA"
    )

    def table_rows(rows):
        out = []
        for row in rows:
            status = row["Motivo acompanhamento"] or "ENCERRADO"
            badge = "closed" if row["Encerrado"] == "SIM" else "open"
            if row["Encontrado SAP"] == "NAO":
                badge = "new"

            out.append(
                "<tr>"
                f"<td><b>{html.escape(str(row['Pedido Ariba']))}</b></td>"
                f"<td>{html.escape(str(row['Versao Ariba'] or ''))}</td>"
                f"<td>{html.escape(str(row['Data Ariba'] or ''))}</td>"
                f"<td><span class='badge {badge}'>{html.escape(status)}</span></td>"
                f"<td>{html.escape(str(row['DocNum'] or '-'))}</td>"
                f"<td>{html.escape(str(row['CardCode'] or '-'))}</td>"
                f"<td>{html.escape(str(row['Posicao SAP'] or '-'))}</td>"
                "</tr>"
            )
        return "\n".join(out)

    period_start = db.get_meta("validation_period_start", "-")
    period_end = db.get_meta("validation_period_end", "-")
    versions = db.counts()["versions"]

    document = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Monitor Ariba x SAP</title>
<style>
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: "Segoe UI", Arial, sans-serif;
  background: #f3f5f7;
  color: #1f2937;
}}
.header {{
  background: #111827;
  color: white;
  padding: 28px 34px;
}}
.header h1 {{
  margin: 0 0 6px;
  font-size: 28px;
}}
.header .sub {{
  color: #cbd5e1;
  font-size: 14px;
}}
.container {{
  max-width: 1600px;
  margin: 0 auto;
  padding: 26px;
}}
.validation {{
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 20px;
  font-weight: 600;
}}
.validation.ok {{
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
}}
.validation.warn {{
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
}}
.meta {{
  font-weight: 400;
  margin-top: 6px;
  color: inherit;
  opacity: .85;
}}
.cards {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}}
.card {{
  background: white;
  border-radius: 12px;
  padding: 18px 20px;
  border-left: 5px solid #94a3b8;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}}
.card.blue {{ border-left-color: #2563eb; }}
.card.green {{ border-left-color: #16a34a; }}
.card.orange {{ border-left-color: #ea580c; }}
.card.red {{ border-left-color: #dc2626; }}
.card.gray {{ border-left-color: #64748b; }}
.card-number {{
  font-size: 30px;
  font-weight: 700;
}}
.card-label {{
  margin-top: 4px;
  color: #475569;
  font-weight: 600;
}}
.panel {{
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,.05);
  margin-bottom: 20px;
}}
.panel h2 {{
  margin-top: 0;
  font-size: 20px;
}}
.note {{
  color: #64748b;
  margin-top: -8px;
  margin-bottom: 18px;
}}
table {{
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
}}
th {{
  text-align: left;
  padding: 10px;
  background: #f8fafc;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}}
td {{
  padding: 10px;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: top;
}}
tr:hover td {{
  background: #fafafa;
}}
.badge {{
  display: inline-block;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
}}
.badge.open {{
  background: #fff7ed;
  color: #9a3412;
}}
.badge.new {{
  background: #fef2f2;
  color: #991b1b;
}}
.badge.closed {{
  background: #ecfdf5;
  color: #065f46;
}}
.files {{
  display: grid;
  gap: 8px;
  color: #475569;
}}
.footer {{
  color: #64748b;
  font-size: 12px;
  margin-top: 18px;
}}
</style>
</head>
<body>
<div class="header">
  <h1>Monitor Ariba x SAP Business One</h1>
  <div class="sub">
    Painel operacional Brasmo • atualizado em {local_now_text()}
  </div>
</div>

<div class="container">
  <div class="validation {validation_class}">
    {validation_text}
    <div class="meta">
      Periodo validado: {html.escape(period_start)} ate {html.escape(period_end)}
      • {len(audit)} pedidos unicos
      • {versions} registros/versoes Ariba armazenados
      • conclusao SAP: {html.escape(validation_done or '-')}
    </div>
  </div>

  <div class="cards">
    {cards_html}
  </div>

  <div class="panel">
    <h2>Pedidos que exigem acompanhamento</h2>
    <div class="note">
      FATURADO, EXPEDIDO e CANCELADO sao considerados encerrados.
      Se um mesmo pedido tiver varios DocNum, ele so desaparece quando todos
      estiverem encerrados.
    </div>
    <table>
      <thead>
        <tr>
          <th>Pedido Ariba</th>
          <th>Versao</th>
          <th>Data Ariba</th>
          <th>Motivo</th>
          <th>DocNum</th>
          <th>Cliente</th>
          <th>Posicao SAP</th>
        </tr>
      </thead>
      <tbody>
        {table_rows(open_rows) if open_rows else '<tr><td colspan="7">Nenhuma pendencia.</td></tr>'}
      </tbody>
    </table>
  </div>

  <div class="panel">
    <h2>Arquivos de auditoria</h2>
    <div class="files">
      <div><b>auditoria_90_dias.csv</b> — todos os pedidos conferidos Ariba x SAP.</div>
      <div><b>pedidos_em_acompanhamento.csv</b> — somente o que ainda exige atencao.</div>
      <div><b>historico_ariba_90_dias.csv</b> — registros e versoes recebidos do Ariba.</div>
      <div><b>resumo_validacao.txt</b> — resumo simples da ultima validacao.</div>
    </div>
  </div>

  <div class="footer">
    Os dados encerrados permanecem gravados no banco SQLite e no CSV de auditoria,
    mesmo quando deixam de aparecer na lista operacional.
  </div>
</div>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
    return path


def export_all(db):
    settings.ensure_dirs()
    return {
        "audit": export_audit_csv(db),
        "open": export_open_csv(db),
        "ariba": export_ariba_versions_csv(db),
        "summary": export_summary_txt(db),
        "html": export_html(db),
    }
