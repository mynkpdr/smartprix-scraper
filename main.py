"""
Daily Smartprix mobile scraper with URL-based progress tracking.
Processes a batch of mobiles per run, resumes from last progress,
saves results, and tracks last modification date.
"""

import xml.etree.ElementTree as ET
import json
import pandas as pd
import time
import os
import re
import cloudscraper

# ----------------------------
# CONFIG
# ----------------------------
PRODUCT_TYPE = os.getenv("PRODUCT_TYPE", "mobiles")  # default to mobiles
SITEMAP_URL = f"https://www.smartprix.com/sitemaps/in/{PRODUCT_TYPE}.xml"
API_BASE = "https://www.smartprix.com/ui/api/page-info?k="
BATCH_SIZE = 100  # Number of products to process per run
PROGRESS_FILE = os.path.join("data", f"{PRODUCT_TYPE}/{PRODUCT_TYPE}_progress.json")
CSV_FILE = os.path.join("data", f"{PRODUCT_TYPE}/{PRODUCT_TYPE}.csv")

os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

# ----------------------------
# Encoder Function
# ----------------------------
Aa = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"

def Sa(e: dict) -> str:
    if not e:
        return ""
    t = json.dumps(e, separators=(",", ":"))
    n = "1"
    for ch in t:
        code = ord(ch)
        if code > 127:
            n += ch
        else:
            code %= 95
            if code < 64:
                n += Aa[code]
            else:
                n += "." + Aa[code & 63]
    return n

# ----------------------------
# cloudscraper Session
# ----------------------------
def get_session():
    """Returns a cloudscraper session to bypass Cloudflare"""
    return cloudscraper.create_scraper()

# ----------------------------
# Sitemap + Endpoint Extraction
# ----------------------------
def fetch_sitemap(session):
    resp = session.get(SITEMAP_URL)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    # Extract URLs and lastmod
    entries = []
    for url_el in root.findall(".//{*}url"):
        loc = url_el.find("{*}loc")
        lastmod = url_el.find("{*}lastmod")
        entry = {
            "url": loc.text if loc is not None else None,
            "lastmod": lastmod.text if lastmod is not None else None
        }
        if entry["url"]:
            entries.append(entry)
    return entries

def extract_endpoint(entry):
    match = re.search(r"/" + PRODUCT_TYPE + r"/[^/]+$", entry["url"])
    return {"url": match.group(0), "lastmod": entry["lastmod"]} if match else None

# ----------------------------
# Fetch product data
# ----------------------------
def fetch_product_data(session, endpoint):
    t = int(time.time() * 1000)
    st = t - 5000
    payload = {"url": endpoint, "data": {}, "t": t, "st": st}
    key = Sa(payload)
    api_url = f"{API_BASE}{key}"
    print(api_url)
    resp = session.get(api_url)
    resp.raise_for_status()
    return resp.json()

# ----------------------------
# Parse product
# ----------------------------
def parse_product(data, lastmod):
    item = data.get("item", {})
    full_specs = item.get("fullSpecs", [])

    result = {}

    # Flatten fullSpecs
    for category in full_specs:
        title = category.get("title")
        items = category.get("items", [])
        if title:
            for spec in items:
                spec_title = spec.get("title")
                spec_description = spec.get("description")
                if spec_title:
                    col_name = f"{title}.{spec_title}"
                    result[col_name] = spec_description

    result.update({
        "Name": item.get("name"),
        "Brand": item.get("brand", {}).get("name"),
        "Price": item.get("price"),
        "Price Drop": item.get("priceDrop"),
        "Price Drop Amount": item.get("priceDropAmount"),
        "Last modified": lastmod,
        "Related Items": json.dumps([
            {"Name": x.get("name"), "Price": x.get("price")}
            for x in item.get("relatedItems", {}).get("products", [])
        ], ensure_ascii=False),
    })
    return result

# ----------------------------
# Progress Tracking
# ----------------------------
def load_progress():
    """Load processed URLs from progress file"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except:
                return set()
    return set()

def save_progress(processed_urls):
    """Save processed URLs to progress file"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed_urls), f, ensure_ascii=False, indent=2)

# ----------------------------
# Main Workflow
# ----------------------------
def main():
    session = get_session()
    print("Fetching sitemap...")
    urls = fetch_sitemap(session)
    endpoints = [extract_endpoint(u) for u in urls if extract_endpoint(u)]
    print(f"Found {len(endpoints)} total products.")

    processed_urls = load_progress()
    print(f"Already processed {len(processed_urls)} products.")

    # Filter endpoints that are not yet processed
    to_process = [ep for ep in endpoints if ep["url"] not in processed_urls]
    batch = to_process[:BATCH_SIZE]

    if not batch:
        print("All products are already processed.")
        return

    print(f"Processing batch of {len(batch)} products...")

    all_results = []
    for i, ep in enumerate(batch):
        try:
            data = fetch_product_data(session, ep["url"])
            parsed = parse_product(data, ep["lastmod"])
            all_results.append(parsed)
            processed_urls.add(ep["url"])  # Mark URL as processed
            print(f"({i+1}/{len(batch)}) Fetched: {parsed.get('Name')}")
            time.sleep(1)  # polite delay
        except Exception as e:
            print(f"Error fetching {ep['url']}: {e}")

    if all_results:
        df_new = pd.json_normalize(all_results, sep=".")

        if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
            # Load existing data
            df_existing = pd.read_csv(CSV_FILE)

            # Merge both, aligning columns
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)

            # Ensure consistent column order (sort or keep as first seen)
            df_combined = df_combined.reindex(
                sorted(df_combined.columns), axis=1
            )

            # Overwrite CSV
            df_combined.to_csv(CSV_FILE, index=False, encoding="utf-8")
        else:
            # First time writing
            df_new.to_csv(CSV_FILE, index=False, encoding="utf-8")

        print(f"Successfully saved {len(all_results)} products to {CSV_FILE}.")


    save_progress(processed_urls)
    print(f"Progress saved for {len(processed_urls)} URLs.")

if __name__ == "__main__":
    main()
