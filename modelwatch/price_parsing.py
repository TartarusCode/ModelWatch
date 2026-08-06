from decimal import Decimal


def is_known_price(token: Decimal) -> bool:
    return token >= 0


def parse_per_token(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except Exception:
        return None
