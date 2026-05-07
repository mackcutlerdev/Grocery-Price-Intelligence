import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def get_products_for_banner(banner_id: int) -> list[dict]:
    response = supabase.table("product_aliases") \
        .select("product_id, banner_sku") \
        .eq("banner_id", banner_id) \
        .execute()
    return [{"product_id": r["product_id"], "sku": r["banner_sku"]} for r in response.data]