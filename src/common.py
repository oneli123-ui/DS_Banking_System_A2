from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import uuid

MONEY_Q = Decimal("0.01")

def money(x: str | int | float | Decimal) -> Decimal:
    return Decimal(str(x)).quantize(MONEY_Q, rounding=ROUND_HALF_UP)

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

@dataclass(frozen=True)
class FeeRule:
    min_exclusive: Decimal
    max_inclusive: Decimal | None
    pct: Decimal
    cap: Decimal | None

FEE_RULES = [
    FeeRule(money("0.00"),     money("2000.00"),   Decimal("0.00"),    None),
    FeeRule(money("2000.00"),  money("10000.00"),  Decimal("0.0025"),  money("20.00")),
    FeeRule(money("10000.00"), money("20000.00"),  Decimal("0.0020"),  money("25.00")),
    FeeRule(money("20000.00"), money("50000.00"),  Decimal("0.00125"), money("40.00")),
    FeeRule(money("50000.00"), money("100000.00"), Decimal("0.0008"),  money("50.00")),
    FeeRule(money("100000.00"), None,              Decimal("0.0005"),  money("100.00")),
]

def compute_fee(amount: Decimal) -> Decimal:
    for rule in FEE_RULES:
        if amount > rule.min_exclusive and (rule.max_inclusive is None or amount <= rule.max_inclusive):
            fee = (amount * rule.pct).quantize(MONEY_Q, rounding=ROUND_HALF_UP)
            if rule.cap is not None and fee > rule.cap:
                fee = rule.cap
            return fee
    return money("0.00")
