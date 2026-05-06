import re
import requests
import json
import time
import pandas as pd

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, parse_qs


def get_amazon_product_data(
    asin: str,
    api_key,
    domain
) -> dict:
    """
    Fetch reviews for a given ASIN from the Rainforest API.

    Returns:
        Parsed JSON response from the Rainforest API as a dict.
    """
    params = {
        'api_key': api_key,
        'amazon_domain': domain,
        'asin': asin,
        'type': 'product',
        'output': 'json',
    }

    # Make the HTTP GET request to Rainforest API
    api_result = requests.get('https://api.rainforestapi.com/request', params=params, timeout=20)

    # Check HTTP status
    if api_result.status_code in (401, 403):
        raise RuntimeError(f"Rainforest API auth failed (HTTP {api_result.status_code}). Check API key.")
    if api_result.status_code == 404:
        raise RuntimeError(f"ASIN {asin} not found on {domain}.")
    if not api_result.ok:
        raise RuntimeError(f"Rainforest API returned HTTP {api_result.status_code}: {api_result.text[:200]}")

    return api_result.json()


def _fetch_with_timing(asin: str, api_key, domain) -> tuple:
    """Wrapper that times a single fetch. Returns (asin, data, elapsed_seconds)."""
    start = time.perf_counter()
    data = get_amazon_product_data(asin, api_key, domain)
    elapsed = time.perf_counter() - start
    return asin, data, elapsed



def get_amazon_product_data_parallel(
    asin_list: List[str],
    api_key,
    domain,
) -> dict:
    """
    Fetch product data for a list of ASINs in parallel.
    Silently skips any ASIN whose request fails (still logs the failure).

    Returns:
        Dict mapping asin -> parsed Rainforest JSON response, only for successful fetches.
        Returns an empty dict if asin_list is empty or all fetches fail.
    """
    if not asin_list:
        return {}

    results: dict = {}
    max_workers = min(len(asin_list), 5)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_asin = {
            executor.submit(_fetch_with_timing, asin, api_key, domain): asin
            for asin in asin_list
        }

        for future in as_completed(future_to_asin):
            asin = future_to_asin[future]
            try:
                _, data, elapsed = future.result()
                results[asin] = data
            except Exception as e:
                # Skip this ASIN but keep processing the rest
                print(f"Failed to fetch ASIN {asin}: {e}")
                continue

    return results


def get_feature_bullets_from_json(data):
    """Return feature_bullets joined into a single string, separated by \\n\\n.
    Returns empty string if data is malformed or bullets are missing."""
    if not isinstance(data, dict):
        return ""
    product = data.get("product") or {}
    if not isinstance(product, dict):
        return ""
    bullets = product.get("feature_bullets") or []
    if not isinstance(bullets, list):
        return ""
    # Filter out any non-string or empty entries defensively
    bullets = [b for b in bullets if isinstance(b, str) and b.strip()]
    return "\n\n".join(bullets)


def get_all_feature_bullets(json_data):
    """Return all feature bullets across ASINs as a flat list[str].
    Returns empty list if json_data is None, empty, or malformed."""
    if not json_data or not isinstance(json_data, dict):
        return []
    bullets = []
    for asin_json in json_data.values():
        text = get_feature_bullets_from_json(asin_json)
        if text:
            bullets.append(text)
    return bullets

def get_reviews_from_json(data):
    """Return top_reviews as a DataFrame with normalized columns.

    Accepts either:
    - A single product dict: {"product": {...}}
    - A multi-product dict: {"ASIN1": {"product": {...}}, "ASIN2": ...}
    """
    empty_df = pd.DataFrame(columns=[
        "asin", "product_title", "review_id", "title",
        "review_date", "rating", "helpful_votes", "review_text"
    ])

    if not isinstance(data, dict):
        return empty_df

    try:
        entries = [data] if "product" in data else list(data.values())
        rows = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            product = entry.get("product", {})
            if not isinstance(product, dict):
                continue
            product_title = product.get("title")
            reviews = product.get("top_reviews", []) or []
            for r in reviews:
                if not isinstance(r, dict):
                    continue
                utc = (r.get("date") or {}).get("utc")
                review_date = utc[:10] if utc else None
                rows.append({
                    "asin": r.get("asin"),
                    "product_title": product_title,
                    "review_id": r.get("id"),
                    "title": r.get("title"),
                    "review_date": review_date,
                    "rating": r.get("rating"),
                    "helpful_votes": r.get("helpful_votes") or 0,
                    "review_text": r.get("body"),
                })

        if not rows:
            return empty_df

        df = pd.DataFrame(rows, columns=[
            "asin", "product_title", "review_id", "title",
            "review_date", "rating", "helpful_votes", "review_text"
        ])
        df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
        return df

    except Exception:
        return empty_df


def get_all_reviews(json_data):
    """Return concatenated reviews across ASINs as a single DataFrame."""
    empty_df = pd.DataFrame(columns=[
        "asin", "product_title", "review_id", "title",
        "review_date", "rating", "helpful_votes", "review_text"
    ])

    if not isinstance(json_data, dict) or not json_data:
        return empty_df

    try:
        dfs = [get_reviews_from_json(entry) for entry in json_data.values()]
        dfs = [df for df in dfs if not df.empty]

        if not dfs:
            return empty_df

        review_df = pd.concat(dfs, ignore_index=True)
        review_df = review_df.sort_values(by=["asin", "helpful_votes"], ascending=False)
        review_df = review_df[~review_df['review_text'].isna()]

        return review_df

    except Exception:
        return empty_df
    

def concatenate_reviews(df):
    def remove_emojis(text):
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F9FF"
            u"\U00002700-\U000027BF"
            u"\U0001FA00-\U0001FA6F"
            u"\U0001FA70-\U0001FAFF"
            u"\U00002500-\U00002BEF"
            u"\U00010000-\U0010FFFF"
        "]+", flags=re.UNICODE)
        return emoji_pattern.sub("", text).strip()

    if not isinstance(df, pd.DataFrame) or df.empty:
        return ""

    required_cols = {"product_title", "title", "review_text", "rating", "helpful_votes"}
    if not required_cols.issubset(df.columns):
        return ""

    all_empty = df['review_text'].isna() | (df['review_text'].str.strip() == '')
    if all_empty.all():
        return ""

    try:
        products = []
        for p_idx, (product_title, group) in enumerate(df.groupby("product_title", sort=False)):
            reviews = []
            for i, (_, row) in enumerate(group.iterrows()):
                try:
                    rating = f"{row['rating']}/5 stars"
                    title = remove_emojis(str(row["title"])) if pd.notna(row["title"]) else ""
                    body = remove_emojis(str(row["review_text"])) if pd.notna(row["review_text"]) else ""
                    helpful = int(row["helpful_votes"]) if pd.notna(row["helpful_votes"]) else 0
                    helpful_line = f"\n{helpful} {'person' if helpful == 1 else 'people'} found this helpful" if helpful >= 1 else ""
                    reviews.append(f"Review {i+1} ({rating}): {title}\n{body}{helpful_line}")
                except Exception:
                    continue
            if reviews:
                product_block = f"Product {p_idx+1}: {product_title}\n\n" + "\n\n".join(reviews)
                products.append(product_block)
        return "\n\n".join(products)
    except Exception:
        return ""