import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json


# ============================================================
# REQUEST HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ============================================================
# COMMON PRICE EXTRACTOR
# ============================================================

def extract_price(text):

    if not text:
        return None

    text = str(text).replace("\xa0", " ")

    # ₹1,299
    match = re.search(
        r"₹\s*([\d,]+(?:\.\d+)?)",
        text
    )

    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except:
            pass

    # Rs 1299
    match = re.search(
        r"Rs\.?\s*([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except:
            pass

    # INR 1299
    match = re.search(
        r"INR\s*([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except:
            pass

    return None


# ============================================================
# JSON-LD PRODUCT EXTRACTOR
# ============================================================

def extract_json_ld_product(soup):

    products = []

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):

        try:

            raw = script.string

            if not raw:
                continue

            data = json.loads(raw)

            if isinstance(data, dict):

                if data.get("@type") == "Product":
                    products.append(data)

                elif isinstance(data.get("@graph"), list):

                    for item in data["@graph"]:

                        if (
                            isinstance(item, dict)
                            and item.get("@type") == "Product"
                        ):
                            products.append(item)

            elif isinstance(data, list):

                for item in data:

                    if (
                        isinstance(item, dict)
                        and item.get("@type") == "Product"
                    ):
                        products.append(item)

        except:
            continue

    if products:
        return products[0]

    return None


# ============================================================
# CROMA
# ============================================================

def scrape_croma(url, response):

    soup = BeautifulSoup(response.text, "html.parser")

    product_name = None
    price = None
    image = None

    meta_title = soup.find(
        "meta",
        property="og:title"
    )

    if meta_title:
        product_name = meta_title.get("content")

    if not product_name:

        h1 = soup.find("h1")

        if h1:
            product_name = h1.get_text(
                " ",
                strip=True
            )

    price_selectors = [
        "span.amount",
        "span[class*='amount']",
        "div[class*='price']",
        "span[class*='price']",
    ]

    for selector in price_selectors:

        element = soup.select_one(selector)

        if element:

            price = extract_price(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if price:
                break

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:
        image = og_image.get("content")

    if not image:

        img = soup.find("img")

        if img:
            image = (
                img.get("src")
                or img.get("data-src")
            )

    if product_name and price:

        print("🎉 Croma scraping successful!")

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ Croma product not found")

    return None


# ============================================================
# RELIANCE DIGITAL
# ============================================================

def scrape_reliance_digital(url, response):

    soup = BeautifulSoup(response.text, "html.parser")

    product_name = None
    price = None
    image = None

    meta_title = soup.find(
        "meta",
        property="og:title"
    )

    if meta_title:
        product_name = meta_title.get("content")

    if not product_name:

        h1 = soup.find("h1")

        if h1:
            product_name = h1.get_text(
                " ",
                strip=True
            )

    price_selectors = [
        "span[class*='price']",
        "div[class*='price']",
        "p[class*='price']",
        "[data-testid*='price']",
    ]

    for selector in price_selectors:

        element = soup.select_one(selector)

        if element:

            price = extract_price(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if price:
                break

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:
        image = og_image.get("content")

    if not image:

        img = soup.find("img")

        if img:
            image = (
                img.get("src")
                or img.get("data-src")
            )

    if product_name and price:

        print("🎉 Reliance Digital scraping successful!")

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ Reliance Digital product not found")

    return None


# ============================================================
# WEBSCRAPER TEST SITE
# ============================================================

def scrape_webscraper(url, response):

    soup = BeautifulSoup(response.text, "html.parser")

    product_name = None
    price = None
    image = None

    name_selectors = [
        "h1",
        "h4",
        ".card-title",
        ".product-name",
    ]

    for selector in name_selectors:

        element = soup.select_one(selector)

        if element:

            product_name = element.get_text(
                " ",
                strip=True
            )

            if product_name:
                break

    price_selectors = [
        ".price",
        ".card-text",
        ".product-price",
    ]

    for selector in price_selectors:

        element = soup.select_one(selector)

        if element:

            price = extract_price(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if price:
                break

    img = soup.find("img")

    if img:

        image = (
            img.get("src")
            or img.get("data-src")
        )

        if image:
            image = urljoin(url, image)

    if product_name and price:

        print("🎉 WebScraper scraping successful!")

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ WebScraper product not found")

    return None


# ============================================================
# FLIPKART
# ============================================================

def scrape_flipkart(url, response):

    soup = BeautifulSoup(response.text, "html.parser")

    product_name = None
    price = None
    image = None

    # PRODUCT NAME

    og_title = soup.find(
        "meta",
        property="og:title"
    )

    if og_title and og_title.get("content"):
        product_name = og_title["content"].strip()

    if not product_name:

        h1 = soup.find("h1")

        if h1:
            product_name = h1.get_text(
                " ",
                strip=True
            )

    # PRICE SELECTORS

    price_selectors = [
        "div.Nx9bqj",
        "div._30jeq3",
        "div.CEmiEU",
        "div._16Jk6d",
        "div._25b18c",
        "div._1_WHN1",
        "span._30jeq3",
        "div.Nx9bqj.CdC2Go",
        "div.hl05eU",
    ]

    for selector in price_selectors:

        element = soup.select_one(selector)

        if element:

            price = extract_price(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if price:
                break

    # JSON FALLBACK

    if not price:

        html = response.text

        patterns = [
            r'"sellingPrice"\s*:\s*"?([\d,.]+)"?',
            r'"selling_price"\s*:\s*"?([\d,.]+)"?',
            r'"sellingPriceValue"\s*:\s*"?([\d,.]+)"?',
            r'"finalPrice"\s*:\s*"?([\d,.]+)"?',
            r'"discountedPrice"\s*:\s*"?([\d,.]+)"?',
            r'"currentPrice"\s*:\s*"?([\d,.]+)"?',
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                html,
                re.IGNORECASE
            )

            if match:

                try:

                    price = float(
                        match.group(1).replace(",", "")
                    )

                    break

                except:
                    pass

    # VISIBLE TEXT FALLBACK

    if not price:

        text = soup.get_text(
            " ",
            strip=True
        )

        patterns = [
            r"₹\s*([\d,]+(?:\.\d+)?)",
            r"Rs\.?\s*([\d,]+(?:\.\d+)?)",
            r"INR\s*([\d,]+(?:\.\d+)?)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                try:

                    price = float(
                        match.group(1).replace(",", "")
                    )

                    break

                except:
                    pass

    # IMAGE

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:
        image = og_image.get("content")

    if not image:

        twitter_image = soup.find(
            "meta",
            attrs={"name": "twitter:image"}
        )

        if twitter_image:
            image = twitter_image.get("content")

    if not image:

        img = soup.find("img")

        if img:
            image = (
                img.get("src")
                or img.get("data-src")
            )

    if product_name and price:

        print("================================")
        print("🎉 Flipkart scraping successful!")
        print("================================")

        print("Product Name:", product_name)
        print("Price:", price)
        print("Image:", image)

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ Flipkart product not found")

    return None


# ============================================================
# MYNTRA
# ============================================================

def scrape_myntra(url, response):

    soup = BeautifulSoup(response.text, "html.parser")

    product_name = None
    price = None
    image = None

    # PRODUCT NAME

    og_title = soup.find(
        "meta",
        property="og:title"
    )

    if og_title and og_title.get("content"):
        product_name = og_title["content"].strip()

    if not product_name:

        h1 = soup.find("h1")

        if h1:
            product_name = h1.get_text(
                " ",
                strip=True
            )

    if not product_name:

        title = soup.find("title")

        if title:
            product_name = title.get_text(
                " ",
                strip=True
            )

    # PRICE

    price_selectors = [
        "span.pdp-price",
        "span.pdp-discountedPrice",
        "div.pdp-price strong",
        "div[class*='pdp-price']",
        "span[class*='pdp-price']",
        "span[class*='Price']",
        "div[class*='Price']",
    ]

    for selector in price_selectors:

        elements = soup.select(selector)

        for element in elements:

            found_price = extract_price(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if found_price:

                price = found_price
                break

        if price:
            break

    # JSON FALLBACK

    if not price:

        html = response.text

        patterns = [
            r'"discountedPrice"\s*:\s*(\d+)',
            r'"sellingPrice"\s*:\s*(\d+)',
            r'"discountedPrice"\s*:\s*"(\d+)"',
            r'"sellingPrice"\s*:\s*"(\d+)"',
            r'"price"\s*:\s*(\d+)',
            r'"price"\s*:\s*"(\d+)"',
        ]

        for pattern in patterns:

            matches = re.findall(
                pattern,
                html,
                re.IGNORECASE
            )

            for value in matches:

                try:

                    found_price = float(
                        str(value).replace(",", "")
                    )

                    if found_price > 0:

                        price = found_price
                        break

                except:
                    pass

            if price:
                break

    # VISIBLE TEXT

    if not price:

        page_text = soup.get_text(
            " ",
            strip=True
        )

        patterns = [
            r"₹\s*([\d,]+(?:\.\d+)?)",
            r"Rs\.?\s*([\d,]+(?:\.\d+)?)",
            r"INR\s*([\d,]+(?:\.\d+)?)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                page_text,
                re.IGNORECASE
            )

            if match:

                try:

                    price = float(
                        match.group(1).replace(",", "")
                    )

                    break

                except:
                    pass

    # IMAGE

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:
        image = og_image.get("content")

    if not image:

        twitter_image = soup.find(
            "meta",
            attrs={"name": "twitter:image"}
        )

        if twitter_image:
            image = twitter_image.get("content")

    if not image:

        img = soup.find("img")

        if img:
            image = (
                img.get("src")
                or img.get("data-src")
            )

    if product_name and price:

        print("================================")
        print("🎉 Myntra scraping successful!")
        print("================================")

        print("Product Name:", product_name)
        print("Price:", price)
        print("Image:", image)

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ Myntra product not found")

    return None


# ============================================================
# AJIO
# ============================================================

def scrape_ajio(url, response):

    soup = BeautifulSoup(response.text, "html.parser")

    product_name = None
    price = None
    image = None

    # JSON-LD

    product_data = extract_json_ld_product(soup)

    if product_data:

        product_name = product_data.get("name")

        offers = product_data.get("offers")

        if isinstance(offers, dict):

            price = extract_price(
                offers.get("price")
            )

        elif isinstance(offers, list) and offers:

            price = extract_price(
                offers[0].get("price")
            )

        image_data = product_data.get("image")

        if isinstance(image_data, list) and image_data:
            image = image_data[0]

        elif isinstance(image_data, str):
            image = image_data

    # META TITLE

    if not product_name:

        og_title = soup.find(
            "meta",
            property="og:title"
        )

        if og_title:
            product_name = og_title.get("content")

    # H1

    if not product_name:

        h1 = soup.find("h1")

        if h1:
            product_name = h1.get_text(
                " ",
                strip=True
            )

    # PRICE SELECTORS

    if not price:

        selectors = [
            "[class*='price']",
            "[class*='Price']",
            "[data-testid*='price']",
        ]

        for selector in selectors:

            elements = soup.select(selector)

            for element in elements:

                found = extract_price(
                    element.get_text(
                        " ",
                        strip=True
                    )
                )

                if found:

                    price = found
                    break

            if price:
                break

    # IMAGE

    if not image:

        og_image = soup.find(
            "meta",
            property="og:image"
        )

        if og_image:
            image = og_image.get("content")

    if not image:

        img = soup.find("img")

        if img:

            image = (
                img.get("src")
                or img.get("data-src")
            )

    if product_name and price:

        print("================================")
        print("🎉 AJIO scraping successful!")
        print("================================")

        print("Product Name:", product_name)
        print("Price:", price)
        print("Image:", image)

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ AJIO product not found")

    return None


# ============================================================
# MEESHO
# ============================================================

def scrape_meesho(url, response):

    soup = BeautifulSoup(response.text, "html.parser")

    product_name = None
    price = None
    image = None

    # JSON-LD

    product_data = extract_json_ld_product(soup)

    if product_data:

        product_name = product_data.get("name")

        offers = product_data.get("offers")

        if isinstance(offers, dict):

            price = extract_price(
                offers.get("price")
            )

        elif isinstance(offers, list) and offers:

            price = extract_price(
                offers[0].get("price")
            )

        image_data = product_data.get("image")

        if isinstance(image_data, list) and image_data:
            image = image_data[0]

        elif isinstance(image_data, str):
            image = image_data

    # META TITLE

    if not product_name:

        og_title = soup.find(
            "meta",
            property="og:title"
        )

        if og_title:
            product_name = og_title.get("content")

    # H1

    if not product_name:

        h1 = soup.find("h1")

        if h1:
            product_name = h1.get_text(
                " ",
                strip=True
            )

    # PRICE SELECTORS

    if not price:

        selectors = [
            "[class*='price']",
            "[class*='Price']",
            "[data-testid*='price']",
        ]

        for selector in selectors:

            elements = soup.select(selector)

            for element in elements:

                found = extract_price(
                    element.get_text(
                        " ",
                        strip=True
                    )
                )

                if found:

                    price = found
                    break

            if price:
                break

    # IMAGE

    if not image:

        og_image = soup.find(
            "meta",
            property="og:image"
        )

        if og_image:
            image = og_image.get("content")

    if not image:

        img = soup.find("img")

        if img:

            image = (
                img.get("src")
                or img.get("data-src")
            )

    if product_name and price:

        print("================================")
        print("🎉 Meesho scraping successful!")
        print("================================")

        print("Product Name:", product_name)
        print("Price:", price)
        print("Image:", image)

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ Meesho product not found")

    return None


# ============================================================
# BROWSER FETCH
# AJIO / MEESHO 403 FALLBACK
# ============================================================

def fetch_with_browser(url):

    try:

        from playwright.sync_api import sync_playwright

    except ImportError:

        print("❌ Playwright is not installed.")
        print("Run:")
        print("pip install playwright")
        print("playwright install chromium")
        return None

    print()
    print("🌐 Browser fallback started...")
    print("Opening product page...")

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True
            )

            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                viewport={
                    "width": 1366,
                    "height": 768
                },
                locale="en-US"
            )

            page = context.new_page()

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            page.wait_for_timeout(5000)

            html = page.content()

            browser.close()

            if not html:

                print("❌ Browser returned empty HTML")

                return None

            print("✅ Browser page loaded")

            return html

    except Exception as e:

        print("❌ Browser Error:", e)

        return None


# ============================================================
# BROWSER SCRAPER FOR AJIO
# ============================================================

def scrape_ajio_browser(url):

    html = fetch_with_browser(url)

    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    product_name = None
    price = None
    image = None

    # JSON-LD

    product_data = extract_json_ld_product(soup)

    if product_data:

        product_name = product_data.get("name")

        offers = product_data.get("offers")

        if isinstance(offers, dict):

            price = extract_price(
                offers.get("price")
            )

        elif isinstance(offers, list) and offers:

            price = extract_price(
                offers[0].get("price")
            )

        image_data = product_data.get("image")

        if isinstance(image_data, list) and image_data:
            image = image_data[0]

        elif isinstance(image_data, str):
            image = image_data

    # META

    if not product_name:

        meta = soup.find(
            "meta",
            property="og:title"
        )

        if meta:
            product_name = meta.get("content")

    # H1

    if not product_name:

        h1 = soup.find("h1")

        if h1:
            product_name = h1.get_text(
                " ",
                strip=True
            )

    # PRICE

    if not price:

        text = soup.get_text(
            " ",
            strip=True
        )

        matches = re.findall(
            r"₹\s*([\d,]+(?:\.\d+)?)",
            text
        )

        for value in matches:

            try:

                found = float(
                    value.replace(",", "")
                )

                if found > 0:

                    price = found
                    break

            except:
                pass

    # IMAGE

    if not image:

        meta = soup.find(
            "meta",
            property="og:image"
        )

        if meta:
            image = meta.get("content")

    if product_name and price:

        print("================================")
        print("🎉 AJIO browser scraping successful!")
        print("================================")

        print("Product Name:", product_name)
        print("Price:", price)
        print("Image:", image)

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ AJIO browser scraper could not extract product")

    return None


# ============================================================
# BROWSER SCRAPER FOR MEESHO
# ============================================================

def scrape_meesho_browser(url):

    html = fetch_with_browser(url)

    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    product_name = None
    price = None
    image = None

    # JSON-LD

    product_data = extract_json_ld_product(soup)

    if product_data:

        product_name = product_data.get("name")

        offers = product_data.get("offers")

        if isinstance(offers, dict):

            price = extract_price(
                offers.get("price")
            )

        elif isinstance(offers, list) and offers:

            price = extract_price(
                offers[0].get("price")
            )

        image_data = product_data.get("image")

        if isinstance(image_data, list) and image_data:
            image = image_data[0]

        elif isinstance(image_data, str):
            image = image_data

    # META

    if not product_name:

        meta = soup.find(
            "meta",
            property="og:title"
        )

        if meta:
            product_name = meta.get("content")

    # H1

    if not product_name:

        h1 = soup.find("h1")

        if h1:
            product_name = h1.get_text(
                " ",
                strip=True
            )

    # PRICE

    if not price:

        text = soup.get_text(
            " ",
            strip=True
        )

        patterns = [
            r"₹\s*([\d,]+(?:\.\d+)?)",
            r"Rs\.?\s*([\d,]+(?:\.\d+)?)",
        ]

        for pattern in patterns:

            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE
            )

            for value in matches:

                try:

                    found = float(
                        value.replace(",", "")
                    )

                    if found > 0:

                        price = found
                        break

                except:
                    pass

            if price:
                break

    # IMAGE

    if not image:

        meta = soup.find(
            "meta",
            property="og:image"
        )

        if meta:
            image = meta.get("content")

    if product_name and price:

        print("================================")
        print("🎉 Meesho browser scraping successful!")
        print("================================")

        print("Product Name:", product_name)
        print("Price:", price)
        print("Image:", image)

        return {
            "name": product_name,
            "price": price,
            "image": image
        }

    print("❌ Meesho browser scraper could not extract product")

    return None


# ============================================================
# MAIN SCRAPER
# ============================================================

def scrape_product(url):

    print()
    print("================================")
    print("PriceLens Scraper")
    print("================================")

    # Remove accidental ? or &
    url = url.rstrip("?& ")

    print("URL:", url)

    url_lower = url.lower()

    # ========================================================
    # WEBSITE DETECTION
    # ========================================================

    if "croma.com" in url_lower:

        website = "croma"

    elif "reliancedigital.in" in url_lower:

        website = "reliance_digital"

    elif "flipkart.com" in url_lower:

        website = "flipkart"

    elif "myntra.com" in url_lower:

        website = "myntra"

    elif "ajio.com" in url_lower:

        website = "ajio"

    elif "meesho.com" in url_lower:

        website = "meesho"

    else:

        website = "webscraper"

    print("Detected Website:", website)

    # ========================================================
    # AJIO
    # ========================================================

    if website == "ajio":

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20
            )

            print(
                "Response Status:",
                response.status_code
            )

        except Exception as e:

            print("❌ AJIO Request Error:", e)
            response = None

        if response and response.status_code == 200:

            result = scrape_ajio(
                url,
                response
            )

            if result:
                return result

        else:

            if response:
                print(
                    "⚠️ AJIO blocked normal request."
                )
                print(
                    "⚠️ Status:",
                    response.status_code
                )

        # Browser fallback

        print("🔄 Trying AJIO browser fallback...")

        return scrape_ajio_browser(url)

    # ========================================================
    # MEESHO
    # ========================================================

    if website == "meesho":

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20
            )

            print(
                "Response Status:",
                response.status_code
            )

        except Exception as e:

            print("❌ Meesho Request Error:", e)
            response = None

        if response and response.status_code == 200:

            result = scrape_meesho(
                url,
                response
            )

            if result:
                return result

        else:

            if response:
                print(
                    "⚠️ Meesho blocked normal request."
                )
                print(
                    "⚠️ Status:",
                    response.status_code
                )

        # Browser fallback

        print("🔄 Trying Meesho browser fallback...")

        return scrape_meesho_browser(url)

    # ========================================================
    # NORMAL REQUEST FOR OTHER SITES
    # ========================================================

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        print(
            "Response Status:",
            response.status_code
        )

    except Exception as e:

        print("❌ Request Error:", e)

        return None

    # ========================================================
    # RESPONSE CHECK
    # ========================================================

    if response.status_code != 200:

        print(
            "❌ Website returned status:",
            response.status_code
        )

        return None

    # ========================================================
    # WEBSITE-SPECIFIC SCRAPER
    # ========================================================

    if website == "croma":

        return scrape_croma(
            url,
            response
        )

    elif website == "reliance_digital":

        return scrape_reliance_digital(
            url,
            response
        )

    elif website == "flipkart":

        return scrape_flipkart(
            url,
            response
        )

    elif website == "myntra":

        return scrape_myntra(
            url,
            response
        )

    else:

        return scrape_webscraper(
            url,
            response
        )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    test_url = input(
        "Enter product URL: "
    ).strip()

    result = scrape_product(
        test_url
    )

    print()

    if result:

        print("================================")
        print("FINAL RESULT")
        print("================================")

        print(
            "Product Name:",
            result["name"]
        )

        print(
            "Price:",
            result["price"]
        )

        print(
            "Image:",
            result["image"]
        )

    else:

        print("❌ Scraping failed")