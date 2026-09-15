from config import settings
from utils import normalize_text


def sap_position(order):
    """
    Aceita tanto o objeto original retornado pela Service Layer
    quanto um registro ja armazenado no SQLite.
    """

    # Service Layer usa "Cancelled".
    # SQLite armazena como "cancelled".
    cancelled = normalize_text(
        order.get("Cancelled")
        if order.get("Cancelled") is not None
        else order.get("cancelled")
    )

    if cancelled in {"TYES", "YES", "Y"}:
        return "CANCELADO"

    # Service Layer:
    # U_S7T_PosicaoPed
    #
    # SQLite:
    # position_status
    raw_position = order.get("U_S7T_PosicaoPed")

    if raw_position is None:
        raw_position = order.get("position_status")

    pos = normalize_text(raw_position)

    aliases = {
        "FAT PARCIAL": "FAT. PARCIAL",
        "FAT-PARCIAL": "FAT. PARCIAL",
        "FAT_PARTIAL": "FAT. PARCIAL",
    }

    return aliases.get(pos, pos or "SEM POSICAO")


def classify(orders):
    if not orders:
        return "SEM_SAP"

    positions = [sap_position(order) for order in orders]

    if all(position in settings.final_sap_positions for position in positions):
        return "ENCERRADO"

    return "ACOMPANHAR"


def reasons(orders):
    if not orders:
        return ["NOVO / NAO LOCALIZADO NO SAP"]

    result = []

    for order in orders:
        position = sap_position(order)

        if position not in settings.final_sap_positions and position not in result:
            result.append(position)

    return result
