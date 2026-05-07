import requests
import re
from datetime import datetime, timezone
from src.models import PriceObservation
from src.db.insert import insert_observations

STORE_ID = "1982"
BANNER_ID = 1  # Save-On-Foods in our banners table
BANNER = "saveon"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.saveonfoods.com",
    "Referer": "https://www.saveonfoods.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "x-site-host": "https://www.saveonfoods.com",
    "x-shopping-mode": "33333333-3333-3333-3333-333333333333",
}


def parse_price(price_str: str) -> float | None:
    """Extract float from strings like '$25.46 avg/ea' or '$1.87/100g'."""
    if not price_str:
        return None
    match = re.search(r"\$([0-9]+\.?[0-9]*)", price_str)
    return float(match.group(1)) if match else None


def parse_unit_type(unit_price_str: str) -> str:
    """Extract unit type from strings like '$1.87/100g' -> 'per_100g'."""
    if not unit_price_str:
        return "unknown"
    match = re.search(r"/(\d*\s*\w+)$", unit_price_str)
    if match:
        return "per_" + match.group(1).replace(" ", "")
    return "unknown"


def fetch_product(sku: str) -> dict | None:
    url = f"https://storefrontgateway.saveonfoods.com/api/stores/{STORE_ID}/products/{sku}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        print(f"  [ERROR] {sku} returned {response.status_code}")
        return None
    return response.json()


def parse_observation(product_id: int, sku: str, data: dict) -> PriceObservation | None:
    try:
        regular_price = parse_price(data.get("price", ""))
        was_price = parse_price(data.get("wasPrice", ""))
        sale_price = None
        is_on_sale = False

        if was_price:
            sale_price = regular_price
            regular_price = was_price
            is_on_sale = True

        unit_price_str = data.get("unitPrice", "")
        unit_price = parse_price(unit_price_str)
        unit_type = parse_unit_type(unit_price_str)

        return PriceObservation(
            product_id=product_id,
            banner_id=BANNER_ID,
            observed_at=datetime.now(timezone.utc).isoformat(),
            regular_price=regular_price,
            sale_price=sale_price,
            is_on_sale=is_on_sale,
            unit_price=unit_price,
            unit_type=unit_type,
            raw_payload={
                "sku": sku,
                "name": data.get("name"),
                "brand": data.get("brand"),
                "packageSize": str(data.get("unitsOfSize", {}).get("size", "")),
            }
        )
    except Exception as e:
        print(f"  [ERROR] Failed to parse {sku}: {e}")
        return None


def scrape_all(products: list[dict]) -> list[PriceObservation]:
    results = []
    for product in products:
        sku = product["sku"]
        print(f"Fetching {sku}...")
        data = fetch_product(sku)
        if not data:
            continue
        obs = parse_observation(product["product_id"], sku, data)
        if obs:
            results.append(obs)
            print(f"  OK: ${obs.regular_price} | unit: ${obs.unit_price} {obs.unit_type} | on_sale: {obs.is_on_sale}")
    return results


if __name__ == "__main__":
    from src.db.queries import get_products_for_banner

    products = get_products_for_banner(BANNER_ID)
    print(f"Found {len(products)} products for Save-On-Foods")

    if not products:
        # Quick test with one known SKU before aliases are populated
        products = [{"product_id": 23, "sku": "00270483000006"}]
        print("No aliases found, running quick test with ground beef SKU")

    results = scrape_all(products)
    print(f"\nScraped {len(results)} observations")
    insert_observations(results)
    print("Done — check Supabase.")