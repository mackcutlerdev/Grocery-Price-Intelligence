import csv
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

BANNER_IDS = {
    "superstore": 2,
    "saveon": 1,      # Save-On-Foods (to be added later)
    "walmart": 3,     # Walmart Canada (to be added later)
}

def seed_from_csv(path: str):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with engine.begin() as conn:
        for row in rows:
            product_id = int(row["product_id"])
            
            # Upsert into products table
            conn.execute(text("""
                INSERT INTO products (product_id, canonical_name, category, size_value, size_unit)
                VALUES (:product_id, :canonical_name, :category, :size_value, :size_unit)
                ON CONFLICT (product_id) DO UPDATE SET
                    canonical_name = EXCLUDED.canonical_name,
                    category = EXCLUDED.category,
                    size_value = EXCLUDED.size_value,
                    size_unit = EXCLUDED.size_unit
            """), {
                "product_id": product_id,
                "canonical_name": row["canonical_name"],
                "category": row["category"],
                "size_value": float(row["size_value"]) if row["size_value"] else None,
                "size_unit": row["size_unit"] if row["size_unit"] else None,
            })

            # Upsert product_aliases for each banner
            for banner, banner_id in BANNER_IDS.items():
                sku = row.get(f"{banner}_sku", "").strip()
                if not sku:
                    continue
                conn.execute(text("""
                    INSERT INTO product_aliases (product_id, banner_id, banner_sku, banner_product_name)
                    VALUES (:product_id, :banner_id, :banner_sku, :banner_product_name)
                    ON CONFLICT (product_id, banner_id) DO UPDATE SET
                        banner_sku = EXCLUDED.banner_sku
                """), {
                    "product_id": product_id,
                    "banner_id": banner_id,
                    "banner_sku": sku,
                    "banner_product_name": row["canonical_name"],
                })

            print(f"  Seeded product_id={product_id}: {row['canonical_name']}")

    print("\nDone.")


if __name__ == "__main__":
    seed_from_csv("data/basket.csv")