import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from playwright.async_api import async_playwright, Page
import sys, os

STORE_ID = "1556"
BANNER_ID = 2  # Real Canadian Superstore in our banners table

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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

async def scrape_product(page: Page, product_id: int, url: str) -> PriceObservation | None:
    """Scrape a single product page and return a PriceObservation."""
    try:
        full_url = f"{url}?storeId={STORE_ID}" if "storeId" not in url else url
        await page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        # Confirm we're on a real product page, not a 404
        title = await page.title()
        if "404" in title or "unavailable" in title.lower():
            print(f"  [SKIP] Product unavailable: {url}")
            return None

        # --- Price ---
        price_el = page.locator('.product-details-page .selling-price-list__item__price--now-price__value').first
        price_text = await price_el.text_content(timeout=5000)
        regular_price = float(price_text.replace("$", "").strip())

        # --- Sale price (only present when item is actually on sale) ---
        sale_price = None
        is_on_sale = False
        # Only look for was-price WITHIN the sticky price container, not anywhere on the page
        was_price_els = await page.locator(
            '.product-details-page-details__content__sticky-container [data-testid="was-price"]'
        ).all()

        if was_price_els:
            was_text = await was_price_els[0].text_content()
            was_text = was_text.replace("was", "").replace("$", "").strip()
            try:
                sale_price = regular_price
                regular_price = float(was_text)
                is_on_sale = True
            except ValueError:
                pass

        # --- Unit price ---
        unit_el = page.locator('.product-details-page .comparison-price-list__item__price__value').first
        unit_price_text = await unit_el.text_content(timeout=5000)
        unit_price = float(unit_price_text.replace("$", "").strip())

        unit_type_el = page.locator('.product-details-page .comparison-price-list__item__price__unit').first
        unit_type_text = await unit_type_el.text_content(timeout=5000)
        unit_type = unit_type_text.strip().replace("/ ", "per_").replace(" ", "").lower()

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
                "title": title,
                "url": full_url,
                "price_text": price_text,
                "unit_price_text": unit_price_text,
            }
        )

    except Exception as e:
        print(f"  [ERROR] Failed to scrape {url}: {e}")
        return None


async def scrape_all(products: list[dict]) -> list[PriceObservation]:
    """
    Scrape a list of products.
    products = [{"product_id": 1, "url": "https://..."}]
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-CA",
        )
        page = await context.new_page()
        await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")

        # Establish session
        print("Establishing session...")
        await page.goto(
            f"https://www.realcanadiansuperstore.ca/en/?storeId={STORE_ID}",
            wait_until="domcontentloaded",
            timeout=60000
        )
        await page.wait_for_timeout(3000)

        for product in products:
            print(f"Scraping product_id={product['product_id']} ...")
            obs = await scrape_product(page, product["product_id"], product["url"])
            if obs:
                results.append(obs)
                print(f"  OK: ${obs.regular_price} | unit: ${obs.unit_price} {obs.unit_type} | on_sale: {obs.is_on_sale}")
            # Polite delay between requests
            await asyncio.sleep(2)

        await browser.close()

    return results


# --- Quick test ---
if __name__ == "__main__":
    test_products = [
        {
            "product_id": 1,
            "url": "https://www.realcanadiansuperstore.ca/en/2-regular-milk/p/20963512_EA"
        }
    ]

    results = asyncio.run(scrape_all(test_products))
    print(f"\nScraped {len(results)} observations:")
    for r in results:
        print(r)
        
    # Write to database
    from src.db.insert import insert_observations
    insert_observations(results)
    print("Done — check Supabase.")