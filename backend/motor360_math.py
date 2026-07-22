"""Pure financial calculations defined by RFC 001 for Motor 360."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
from typing import Any


MONEY = Decimal("0.01")


def parse_decimal(value: Any) -> Decimal | None:
    """Parse a non-negative Brazilian numeric value without converting null to zero."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        if isinstance(value, Decimal):
            parsed = value
        elif isinstance(value, (int, float)):
            parsed = Decimal(str(value))
        else:
            text = str(value).strip().replace("R$", "").replace(" ", "")
            if "," in text:
                text = text.replace(".", "").replace(",", ".")
            parsed = Decimal(text.replace("%", ""))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() and parsed >= 0 else None


def normalize_percent(value: Any, *, allow_one: bool = True) -> Decimal | None:
    """Normalize 52,25 / 52,25% / 0,5225 to a decimal while preserving null."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    raw_text = str(value).strip()
    parsed = parse_decimal(value)
    if parsed is None:
        return None
    if "%" in raw_text or parsed > 1:
        if parsed > 100:
            return None
        parsed /= Decimal("100")
    if parsed < 0 or parsed > 1 or (not allow_one and parsed >= 1):
        return None
    return parsed


def money(value: Decimal | None) -> float | None:
    return float(value.quantize(MONEY, rounding=ROUND_HALF_UP)) if value is not None else None


def decimal_value(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def months(value: Decimal | None) -> int | None:
    if value is None:
        return None
    return math.ceil(value)


@dataclass(frozen=True)
class ScenarioInput:
    credito_liquido_desejado: Decimal
    recurso_proprio: Decimal
    fgts: Decimal
    parcela_desejada: Decimal
    parcela_maxima_renda: Decimal
    credito_minimo: Decimal | None
    credito_maximo: Decimal | None
    taxa_administracao_total: Decimal | None
    fundo_reserva_total: Decimal | None
    prazo_remanescente: int | None
    percentual_embutido: Decimal | None = None


@dataclass(frozen=True)
class CalculatedScenario:
    id: str
    label: str
    credito_contratado: Decimal | None
    valor_lance_embutido: Decimal | None
    taxa_administracao: Decimal | None
    fundo_reserva: Decimal | None
    saldo_devedor: Decimal | None
    lance_total: Decimal | None
    percentual_lance: Decimal | None
    saldo_apos_lance: Decimal | None
    prazo_inicial_desejada_decimal: Decimal | None
    prazo_inicial_desejada_meses: int | None
    prazo_inicial_limite_renda_decimal: Decimal | None
    prazo_inicial_limite_renda_meses: int | None
    prazo_apos_lance_desejada_decimal: Decimal | None
    prazo_apos_lance_desejada_meses: int | None
    prazo_apos_lance_limite_renda_decimal: Decimal | None
    prazo_apos_lance_limite_renda_meses: int | None
    prazo_remanescente: int | None
    credito_liquido_projetado: Decimal | None
    liquidez_preservada: bool | None
    credit_compatible: bool | None
    term_compatible: bool | None
    income_compatible: bool | None
    data_complete: bool
    creation_status: str
    creation_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key, value in tuple(data.items()):
            if isinstance(value, Decimal):
                data[key] = money(value) if key not in {
                    "percentual_lance",
                } and not key.endswith("_decimal") else decimal_value(value)
        # Backward-compatible aliases used by the current presentation layer.
        data["financial_cost_data_complete"] = self.taxa_administracao is not None and self.fundo_reserva is not None
        data["term_data_complete"] = self.prazo_remanescente_available
        data["analysis_data_complete"] = self.data_complete
        data["financial_data_complete"] = self.data_complete
        data["recommendable"] = False
        data["margem_credito"] = None
        data["alerts"] = []
        def compatible(required_months: int | None) -> bool | None:
            if required_months is None or self.prazo_remanescente is None:
                return None
            return self.prazo_remanescente >= required_months

        data["term_compatible_desired_before_bid"] = compatible(self.prazo_inicial_desejada_meses)
        data["term_compatible_income_before_bid"] = compatible(self.prazo_inicial_limite_renda_meses)
        data["term_compatible_desired_after_bid"] = compatible(self.prazo_apos_lance_desejada_meses)
        data["term_compatible_income_after_bid"] = compatible(self.prazo_apos_lance_limite_renda_meses)
        return data

    @property
    def prazo_remanescente_available(self) -> bool:
        return self.prazo_apos_lance_limite_renda_meses is not None


def _divide(value: Decimal | None, divisor: Decimal) -> Decimal | None:
    if value is None or divisor <= 0:
        return None
    return value / divisor


def calculate_scenario(data: ScenarioInput, *, with_embedded: bool) -> CalculatedScenario:
    """Generate one independent RFC 001 scenario without reading external state."""
    base_liquida = data.credito_liquido_desejado + data.recurso_proprio + data.fgts
    scenario_id = "with_embedded" if with_embedded else "without_embedded"
    label = "Com lance embutido" if with_embedded else "Sem lance embutido"
    embedded = data.percentual_embutido if with_embedded else Decimal("0")
    if with_embedded and (embedded is None or embedded <= 0 or embedded >= 1):
        reason = "percentual_x_ausente" if embedded is None else "percentual_x_invalido"
        return CalculatedScenario(
            id=scenario_id, label=label, credito_contratado=None,
            valor_lance_embutido=None, taxa_administracao=None, fundo_reserva=None,
            saldo_devedor=None, lance_total=None, percentual_lance=None,
            saldo_apos_lance=None, prazo_inicial_desejada_decimal=None,
            prazo_inicial_desejada_meses=None, prazo_inicial_limite_renda_decimal=None,
            prazo_inicial_limite_renda_meses=None, prazo_apos_lance_desejada_decimal=None,
            prazo_apos_lance_desejada_meses=None, prazo_apos_lance_limite_renda_decimal=None,
            prazo_apos_lance_limite_renda_meses=None, prazo_remanescente=data.prazo_remanescente,
            credito_liquido_projetado=None,
            liquidez_preservada=None, credit_compatible=None, term_compatible=None,
            income_compatible=None, data_complete=False, creation_status="not_created",
            creation_reason=reason,
        )

    credito = base_liquida / (Decimal("1") - embedded) if with_embedded else base_liquida
    valor_embutido = credito * embedded
    taxa = credito * data.taxa_administracao_total if data.taxa_administracao_total is not None else None
    fundo = credito * data.fundo_reserva_total if data.fundo_reserva_total is not None else None
    saldo = credito + taxa + fundo if taxa is not None and fundo is not None else None
    lance = data.recurso_proprio + data.fgts + valor_embutido
    percentual_lance = lance / credito if credito > 0 else None
    saldo_apos_lance = max(Decimal("0"), saldo - lance) if saldo is not None else None

    inicial_desejada = _divide(saldo, data.parcela_desejada)
    inicial_renda = _divide(saldo, data.parcela_maxima_renda)
    apos_desejada = _divide(saldo_apos_lance, data.parcela_desejada)
    apos_renda = _divide(saldo_apos_lance, data.parcela_maxima_renda)
    credito_liquido = credito - valor_embutido - data.recurso_proprio - data.fgts
    credit_compatible = (
        data.credito_minimo is not None
        and data.credito_maximo is not None
        and data.credito_minimo <= credito <= data.credito_maximo
    )
    income_compatible = (
        data.prazo_remanescente is not None
        and months(apos_renda) is not None
        and data.prazo_remanescente >= months(apos_renda)
    )
    term_compatible = income_compatible
    data_complete = all((
        data.credito_minimo is not None,
        data.credito_maximo is not None,
        data.taxa_administracao_total is not None,
        data.fundo_reserva_total is not None,
        data.prazo_remanescente is not None,
    ))
    return CalculatedScenario(
        scenario_id, label, credito, valor_embutido, taxa, fundo, saldo, lance,
        percentual_lance, saldo_apos_lance, inicial_desejada, months(inicial_desejada),
        inicial_renda, months(inicial_renda), apos_desejada, months(apos_desejada),
        apos_renda, months(apos_renda), data.prazo_remanescente, credito_liquido,
        credito_liquido.quantize(MONEY, rounding=ROUND_HALF_UP) == data.credito_liquido_desejado.quantize(MONEY, rounding=ROUND_HALF_UP),
        credit_compatible, term_compatible, income_compatible, data_complete,
        "created", None,
    )
