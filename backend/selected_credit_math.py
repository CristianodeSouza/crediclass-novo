"""Server-side financial contract for a selected Motor 360 credit."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .motor360_math import MONEY, money, normalize_percent, parse_decimal


def _rounded(value: Decimal | None) -> float | None:
    return money(value) if value is not None else None


def calculate_selected_credit(*, credit, embedded_percent, administration_rate, reserve_rate, remaining_term, own_bid=0) -> dict:
    gross = parse_decimal(credit)
    if gross is None or gross <= 0:
        raise ValueError("O crédito escolhido deve ser positivo.")
    embedded_ratio = normalize_percent(embedded_percent)
    admin_ratio = normalize_percent(administration_rate)
    reserve_ratio = normalize_percent(reserve_rate)
    if admin_ratio is None or reserve_ratio is None:
        raise ValueError("Taxa administrativa e fundo de reserva precisam estar informados.")
    embedded_ratio = embedded_ratio or Decimal("0")
    term = parse_decimal(remaining_term)
    if term is None or term <= 0:
        raise ValueError("O prazo remanescente precisa ser positivo.")
    own = parse_decimal(own_bid) or Decimal("0")
    embedded = (gross * embedded_ratio).quantize(MONEY, rounding=ROUND_HALF_UP)
    admin = (gross * admin_ratio).quantize(MONEY, rounding=ROUND_HALF_UP)
    reserve = (gross * reserve_ratio).quantize(MONEY, rounding=ROUND_HALF_UP)
    balance = gross + admin + reserve
    installment = (balance / term).quantize(MONEY, rounding=ROUND_HALF_UP) if term and term > 0 else None
    total_bid = own + embedded
    post_installment = (
        (balance - (installment or Decimal("0")) - total_bid) / (term - 1)
    ).quantize(MONEY, rounding=ROUND_HALF_UP) if term and term > 1 and installment is not None else None
    return {
        "contracted_credit": _rounded(gross),
        "embedded_bid": _rounded(embedded),
        "liquid_credit": _rounded(gross - embedded),
        "administration_fee": _rounded(admin),
        "reserve_fee": _rounded(reserve),
        "remaining_balance": _rounded(balance),
        "initial_installment": _rounded(installment),
        "own_bid": _rounded(own),
        "total_bid": _rounded(total_bid),
        "post_contemplation_installment": _rounded(post_installment),
    }
