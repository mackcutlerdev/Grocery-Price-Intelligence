from dataclasses import dataclass

@dataclass
class PriceObservation:
    """
    Represents a single snapshot of a product's pricing data
    collected from a retailer or banner at a specific time

    Each instance captures both normalized fields (like prices)
    and the raw source payload (API/HTML) for traceability/debugging.
    """
    product_id: int
    banner_id: int
    observed_at: str
    regular_price: float
    sale_price: float | None
    is_on_sale: bool
    unit_price: float
    unit_type: str
    raw_payload: dict