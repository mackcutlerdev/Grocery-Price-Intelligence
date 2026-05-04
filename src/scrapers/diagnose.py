import asyncio
from playwright.async_api import async_playwright

STORE_ID = "1556"   # Real Canadian Superstore ID for the 104th Ave location in Surrey BC. We need this because the website denies access if your IP address is outside of the store's area.
PRODUCT_URL = f"https://www.realcanadiansuperstore.ca/en/2-regular-milk/p/20963512_EA?storeId={STORE_ID}"   # URL for 2% Milk 2L for testing the scraper.

async def main():
    # Start Playwright
    async with async_playwright() as p:
        # Launch Chromium browser cause faster usually
        browser = await p.chromium.launch(headless=True)   # Visible window headless=(true || false)
        
        # Create a new browser context with custom settings
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-CA",
        )
        
        # Open a new page then remove webdriver flag to reduce bot detection
        page = await context.new_page()
        await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")

        # Step 1: Load homepage to establish session (like cookies, store context, etc..)
        print("Loading homepage to establish session...")
        await page.goto(
            f"https://www.realcanadiansuperstore.ca/en/?storeId={STORE_ID}",
            wait_until="domcontentloaded", 
            timeout=60000
        )
        # Just wait a bit extra to make sure everything loads properly (had some issues)
        await page.wait_for_timeout(3000)

        # Step 2: Load the specific product page
        print("Loading product page...")
        await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)   # Wait for dynamic stuff to render (like the price)

        # DEBUG: Print page title
        print("Title:", await page.title())

        # Extract the main price using Superstore's HTML formatting (lots of prices, but this one finds the relevant price to the item)
        price = await page.locator('.product-details-page .selling-price-list__item__price--now-price__value').first.text_content()
        unit_price = await page.locator('.product-details-page .comparison-price-list__item__price__value').first.text_content()

        # DEBUG: Print extracted valkues
        print(f"Price: {price}")
        print(f"Unit price: {unit_price}")

        # Close the browser
        await browser.close()

# Run the async script
asyncio.run(main())