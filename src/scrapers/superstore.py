import requests
from datetime import datetime, timezone
from src.models import PriceObservation
from src.db.insert import insert_observations

STORE_ID = "1556"
BANNER_ID = 2
BANNER = "superstore"

# Headers modelled after request/reponse headers observing via DevTools Network API
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en",
    "Business-User-Agent": "PCXWEB",
    "Content-Type": "application/json",
    "Origin": "https://www.realcanadiansuperstore.ca",
    "Referer": "https://www.realcanadiansuperstore.ca/",
    "Site-Banner": BANNER,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "x-apikey": "C1xujSegT5j3ap3yexJjqhOfELwGKYvz",
    "x-application-type": "Web",
    "x-loblaw-tenant-id": "ONLINE_GROCERIES",
}

# Function that fetches the product using it's sku via the relevant API call using headers mimicking browser reqs, and returns the json
def fetch_product(sku: str) -> dict | None:
    date = datetime.now().strftime("%d%m%Y")
    url = (
        f"https://api.pcexpress.ca/pcx-bff/api/v1/products/{sku}"
        f"?lang=en&date={date}&pickupType=STORE&storeId={STORE_ID}&banner={BANNER}"
    )
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        print(f"  [ERROR] {sku} returned {response.status_code}")
        return None
    return response.json()

# Function that parses the JSON for relevant price info and return it to PriceObservation
def parse_observation(product_id: int, sku: str, data: dict) -> PriceObservation | None:
    try:
        offer = data["offers"][0]

        # No sale and default assumption
        regular_price = offer["price"]["value"]
        was_price = offer.get("wasPrice")
        sale_price = None
        is_on_sale = False

        # When there exists a `was_price`, it means there is a sale
        if was_price:
            sale_price = regular_price
            regular_price = was_price["value"]
            is_on_sale = True

        comparison = offer["comparisonPrices"][0] if offer.get("comparisonPrices") else None
        unit_price = comparison["value"] if comparison else 0.0
        unit_type = f"per_{comparison['quantity']}{comparison['unit']}" if comparison else "unknown"

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
                "packageSize": data.get("packageSize"),
            }
        )
    except Exception as e:
        print(f"  [ERROR] Failed to parse {sku}: {e}")
        return None

# Scraping (fetch and process) items via SKU, wihch are either EA based (per item and price is exact) or KG based (per weight and price is ~about)
def scrape_all(products: list[dict]) -> list[PriceObservation]:
    """
    products = [
        {"product_id": 1, "sku": "20963512_EA"},   
        {"product_id": 2, "sku": "20175355001_KG"},
        {"product_id": 3, "sku": "20305674_EA"},
        {"product_id": 4, "sku": "20812144001_EA"},
        {"product_id": 5, "sku": "20325029_EA"}
    ]
    """
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
    print(f"Found {len(products)} products for Superstore")

    results = scrape_all(products)
    print(f"\nScraped {len(results)} observations")
    insert_observations(results)
    print("Done! Check Supabase.")