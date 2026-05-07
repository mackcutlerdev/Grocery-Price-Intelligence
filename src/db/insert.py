import os
from supabase import create_client
from dotenv import load_dotenv
from src.models import PriceObservation

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def insert_observation(obs: PriceObservation) -> None:
    supabase.table("price_observations").insert({
        "product_id": obs.product_id,
        "banner_id": obs.banner_id,
        "observed_at": obs.observed_at,
        "regular_price": obs.regular_price,
        "sale_price": obs.sale_price,
        "is_on_sale": obs.is_on_sale,
        "unit_price": obs.unit_price,
        "unit_type": obs.unit_type,
        "raw_payload": obs.raw_payload,
    }).execute()
    print(f"  Inserted observation for product_id={obs.product_id}")

def insert_observations(observations: list[PriceObservation]) -> None:
    for obs in observations:
        insert_observation(obs)