from dataclasses import dataclass

@dataclass
class PriceObservation:
    product_id: int
    banner_id: int
    observed_at: str
    regular_price: float
    sale_price: float | None
    is_on_sale: bool
    unit_price: float
    unit_type: str
    raw_payload: dict