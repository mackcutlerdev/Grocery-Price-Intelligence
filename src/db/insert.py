import os
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from src.scrapers.superstore import PriceObservation

load_dotenv()

engine = create_engine(os.environ["DATABASE_URL"])


def insert_observation(obs: PriceObservation) -> None:
    sql = text("""
        INSERT INTO price_observations (
            product_id, banner_id, observed_at,
            regular_price, sale_price, is_on_sale,
            unit_price, unit_type, raw_payload
        ) VALUES (
            :product_id, :banner_id, :observed_at,
            :regular_price, :sale_price, :is_on_sale,
            :unit_price, :unit_type, :raw_payload
        )
    """)

    with engine.begin() as conn:
        conn.execute(sql, {
            "product_id": obs.product_id,
            "banner_id": obs.banner_id,
            "observed_at": obs.observed_at,
            "regular_price": obs.regular_price,
            "sale_price": obs.sale_price,
            "is_on_sale": obs.is_on_sale,
            "unit_price": obs.unit_price,
            "unit_type": obs.unit_type,
            "raw_payload": json.dumps(obs.raw_payload),
        })
    print(f"  Inserted observation for product_id={obs.product_id}")


def insert_observations(observations: list[PriceObservation]) -> None:
    for obs in observations:
        insert_observation(obs)