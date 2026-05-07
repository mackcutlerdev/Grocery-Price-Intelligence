import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

def get_products_for_banner(banner_id: int) -> list[dict]:
    """Returns all products that have a SKU for the given banner."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.product_id, p.canonical_name, pa.banner_sku
            FROM products p
            JOIN product_aliases pa ON p.product_id = pa.product_id
            WHERE pa.banner_id = :banner_id
            ORDER BY p.product_id
        """), {"banner_id": banner_id})
        return [{"product_id": r.product_id, "sku": r.banner_sku} for r in rows]