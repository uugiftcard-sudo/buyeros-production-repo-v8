#!/usr/bin/env python3
"""
UK Supermarket Price Scraper — John Lewis & Tesco
==================================================
抓取英国超市/百货商品价格、促销信息
支持：John Lewis、M&S、Tesco

⚠️ 仅供个人比价使用，禁止商业批量采集
"""

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class ProductResult:
    name: str = ""
    brand: str = ""
    price: str = ""
    original_price: str = ""
    currency: str = "GBP"
    unit_price: str = ""          # 每单位价格（如 £/kg）
    category: str = ""
    subcategory: str = ""
    promotion: str = ""           # 促销信息（如 "Save £2", "Half price"）
    rating: str = ""              # 评分
    review_count: str = ""
    availability: str = ""
    image_url: str = ""
    product_url: str = ""
    retailer: str = ""            # John Lewis / Tesco
    search_keyword: str = ""
    scraped_at: str = ""


# ────────────────────────────────────────────────
# John Lewis
# ────────────────────────────────────────────────
def search_john_lewis(keyword: str, limit: int = 30, delay: float = 2.0) -> list[ProductResult]:
    """
    搜索 John Lewis 商品
    官网: https://www.johnlewis.com
    """
    print(f"[INFO] John Lewis 搜索: {keyword}")
    results = []

    # John Lewis Search API
    api_url = "https://www.johnlewis.com/search"
    params = {
        "search-term": keyword,
        "pageSize": limit,
    }

    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # 从 script 标签提取 JSON
        scripts = soup.find_all("script")
        for script in scripts:
            text = script.string or ""
            if '"products"' in text or '"items"' in text or '"results"' in text:
                import re
                # 提取所有 JSON 对象
                json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
                for m in json_matches[:limit]:
                    try:
                        obj = json.loads(m)
                        if obj.get("name") or obj.get("title") or obj.get("productName"):
                            p = ProductResult()
                            p.retailer = "John Lewis"
                            p.search_keyword = keyword
                            p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                            p.name = obj.get("name") or obj.get("title") or obj.get("productName", "")
                            p.brand = obj.get("brand", "")
                            price_info = obj.get("price", {})
                            if isinstance(price_info, dict):
                                p.price = f"£{price_info.get('now', '')}"
                                p.original_price = f"£{price_info.get('was', '')}"
                            else:
                                p.price = str(price_info)
                            p.unit_price = obj.get("unitPrice", "")
                            p.promotion = obj.get("promotion", obj.get("label", ""))
                            p.rating = str(obj.get("rating", ""))
                            p.review_count = str(obj.get("reviewCount", ""))
                            p.availability = obj.get("availability", "")
                            p.image_url = obj.get("image", obj.get("imageUrl", ""))
                            p.product_url = "https://www.johnlewis.com" + obj.get("url", obj.get("productUrl", ""))
                            results.append(p)
                            if len(results) >= limit:
                                break
                    except json.JSONDecodeError:
                        continue
                if results:
                    break

        # HTML 备用解析
        if not results:
            cards = soup.select("[class*='product-card'], [class*='product-item'], [class*='grid-item']")
            for card in cards[:limit]:
                p = ProductResult()
                p.retailer = "John Lewis"
                p.search_keyword = keyword
                p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

                name_tag = card.select_one("[class*='product-name'], [class*='title'], h3, h4, a")
                if name_tag:
                    p.name = name_tag.get_text(strip=True)

                price_tag = card.select_one("[class*='price'], [class*='now']")
                if price_tag:
                    p.price = price_tag.get_text(strip=True)

                promo_tag = card.select_one("[class*='promo'], [class*='label'], [class*='sale']")
                if promo_tag:
                    p.promotion = promo_tag.get_text(strip=True)

                link_tag = card.select_one("a[href*='/p']")
                if link_tag and link_tag.get("href"):
                    p.product_url = "https://www.johnlewis.com" + link_tag["href"]

                if p.name:
                    results.append(p)

        print(f"[✓] John Lewis 找到 {len(results)} 条商品")

    except requests.RequestException as e:
        print(f"[ERROR] John Lewis 请求失败: {e}")

    time.sleep(delay)
    return results


# ────────────────────────────────────────────────
# Tesco
# ────────────────────────────────────────────────
def search_tesco(keyword: str, limit: int = 30, delay: float = 2.0) -> list[ProductResult]:
    """
    搜索 Tesco 商品（ Grocery / Clubcard Deals）
    官网: https://www.tesco.com/groceries
    """
    print(f"[INFO] Tesco 搜索: {keyword}")
    results = []

    # Tesco Groceries Search API (placeholder — scrape-based approach below)
    _api_url = "https:// Tesco.com/groceries/api/products/search"
    _params = {
        "query": keyword,
        "pageSize": limit,
        "group": "Tesco",
    }

    try:
        # 先获取站点
        session = requests.Session()
        session.headers.update(HEADERS)

        # 访问搜索页
        search_url = f"https://www.tesco.com/groceries/en-GB/search?q={requests.utils.quote(keyword)}"
        resp = session.get(search_url, timeout=15)
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # 从 JSON-LD 或 script 提取数据
        scripts = soup.find_all("script")
        for script in scripts:
            text = script.string or ""
            if '"products"' in text or '"items"' in text or '"@type":"Product"' in text:
                import re
                # 提取 Product 对象
                matches = re.findall(
                    r'\{"@type":"Product"[^}]*(?:\{[^}]*\})?[^}]*\}',
                    text
                )
                for m in matches[:limit]:
                    try:
                        obj = json.loads(m)
                        p = ProductResult()
                        p.retailer = "Tesco"
                        p.search_keyword = keyword
                        p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                        p.name = obj.get("name", "")
                        p.brand = obj.get("brand", "")
                        offers = obj.get("offers", {})
                        if isinstance(offers, dict):
                            p.price = offers.get("price", "")
                            p.currency = offers.get("priceCurrency", "GBP")
                        elif isinstance(offers, list) and offers:
                            p.price = offers[0].get("price", "")
                        p.unit_price = obj.get("unitPriceText", "")
                        p.rating = str(obj.get("aggregateRating", {}).get("ratingValue", ""))
                        p.review_count = str(obj.get("aggregateRating", {}).get("reviewCount", ""))
                        img = obj.get("image", [])
                        p.image_url = img[0] if isinstance(img, list) else img
                        results.append(p)
                    except (json.JSONDecodeError, KeyError):
                        continue
                if results:
                    break

        # HTML 备用解析
        if not results:
            items = soup.select("[class*='product-tile'], [class*='product-list'] [class*='item']")
            for item in items[:limit]:
                p = ProductResult()
                p.retailer = "Tesco"
                p.search_keyword = keyword
                p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

                name_tag = item.select_one("[class*='product-name'], h3, h4, a")
                if name_tag:
                    p.name = name_tag.get_text(strip=True)

                price_tag = item.select_one("[class*='price'], [class*='value']")
                if price_tag:
                    p.price = price_tag.get_text(strip=True)

                promo_tag = item.select_one("[class*='promotion'], [class*='deal'], [class*='clubcard']")
                if promo_tag:
                    p.promotion = promo_tag.get_text(strip=True)

                unit_tag = item.select_one("[class*='per'], [class*='unit']")
                if unit_tag:
                    p.unit_price = unit_tag.get_text(strip=True)

                if p.name:
                    results.append(p)

        print(f"[✓] Tesco 找到 {len(results)} 条商品")

    except requests.RequestException as e:
        print(f"[ERROR] Tesco 请求失败: {e}")

    time.sleep(delay)
    return results


# ────────────────────────────────────────────────
# M&S（玛莎百货）— 额外添加
# ────────────────────────────────────────────────
def search_marks_and_spencer(keyword: str, limit: int = 30, delay: float = 2.0) -> list[ProductResult]:
    """搜索 M&S 商品"""
    print(f"[INFO] M&S 搜索: {keyword}")
    results = []

    search_url = f"https://www.marksandspencer.com/search?q={requests.utils.quote(keyword)}"

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        items = soup.select("[class*='product'], [class*='item'], [data-product]")
        for item in items[:limit]:
            p = ProductResult()
            p.retailer = "M&S"
            p.search_keyword = keyword
            p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

            name_tag = item.select_one("[class*='name'], [class*='title'], h3, h4")
            if name_tag:
                p.name = name_tag.get_text(strip=True)

            price_tag = item.select_one("[class*='price'], [class*='now']")
            if price_tag:
                p.price = price_tag.get_text(strip=True)

            link_tag = item.select_one("a[href*='/p/']")
            if link_tag and link_tag.get("href"):
                p.product_url = "https://www.marksandspencer.com" + link_tag["href"]

            if p.name:
                results.append(p)

        print(f"[✓] M&S 找到 {len(results)} 条商品")

    except requests.RequestException as e:
        print(f"[ERROR] M&S 请求失败: {e}")

    time.sleep(delay)
    return results


# ────────────────────────────────────────────────
# 价格对比（所有超市）
# ────────────────────────────────────────────────
def compare_price(keyword: str, delay: float = 2.0) -> list[ProductResult]:
    """在所有支持的超市同时搜索，方便比价"""
    all_results = []
    all_results += search_john_lewis(keyword, delay=delay)
    all_results += search_tesco(keyword, delay=delay)
    all_results += search_marks_and_spencer(keyword, delay=delay)
    return all_results


# ────────────────────────────────────────────────
# 保存
# ────────────────────────────────────────────────
def save_csv(items: list[ProductResult], filename: str):
    if not items:
        print("[INFO] 无数据")
        return
    keys = ["retailer", "name", "brand", "price", "original_price", "unit_price",
            "promotion", "rating", "review_count", "category",
            "availability", "product_url", "search_keyword", "scraped_at"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([asdict(i) for i in items])
    print(f"[✓] 保存 {len(items)} 条 → {filename}")


def save_json(items: list[ProductResult], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump([asdict(i) for i in items], f, ensure_ascii=False, indent=2)
    print(f"[✓] 保存 → {filename}")


def print_summary(items: list[ProductResult]):
    """打印价格对比摘要"""
    if not items:
        return
    print(f"\n📊 价格对比结果 ({len(items)} 条)")
    print("=" * 80)
    # 按价格排序
    priced = [i for i in items if i.price]
    priced.sort(key=lambda x: float(re.sub(r'[^\d.]', '', x.price)) if re.sub(r'[^\d.]', '', x.price) else 9999)
    for p in priced[:15]:
        print(f"  [{p.retailer}] {p.name[:50]:<52} {p.price:>10}  {p.promotion}")
    print("=" * 80)


# ────────────────────────────────────────────────
# 主程序
# ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="英国超市价格爬虫")
    parser.add_argument("--keyword", "-k", help="搜索关键词")
    parser.add_argument("--retailer", "-r", choices=["john-lewis", "tesco", "ms", "all"], default="all")
    parser.add_argument("--limit", "-l", type=int, default=30)
    parser.add_argument("--delay", "-d", type=float, default=2.0, help="请求间隔（秒）")
    parser.add_argument("--compare", "-c", action="store_true", help="价格对比模式（所有超市）")
    parser.add_argument("-o", "--output", default="uk_prices.csv")
    parser.add_argument("-f", "--format", choices=["csv", "json"], default="csv")
    args = parser.parse_args()

    results = []

    if args.compare:
        results = compare_price(args.keyword or "coffee", delay=args.delay)

    elif args.retailer in ("john-lewis", "all"):
        if not args.keyword:
            print("[ERROR] 需要 --keyword")
            return
        results += search_john_lewis(args.keyword, limit=args.limit, delay=args.delay)

    elif args.retailer in ("tesco", "all"):
        if not args.keyword:
            print("[ERROR] 需要 --keyword")
            return
        results += search_tesco(args.keyword, limit=args.limit, delay=args.delay)

    elif args.retailer == "ms":
        if not args.keyword:
            print("[ERROR] 需要 --keyword")
            return
        results += search_marks_and_spencer(args.keyword, limit=args.limit, delay=args.delay)

    else:
        print("""
UK Supermarket Scraper — John Lewis & Tesco
==========================================

# 价格对比（同时搜所有超市）
python uk_supermarket_scraper.py -c -k "whole milk"

# 仅搜 John Lewis
python uk_supermarket_scraper.py -r john-lewis -k "dyson vacuum"

# 仅搜 Tesco
python uk_supermarket_scraper.py -r tesco -k "chicken breast"

# 仅搜 M&S
python uk_supermarket_scraper.py -r ms -k "sandwich"

# 输出 JSON
python uk_supermarket_scraper.py -c -k "coffee" -f json
""")
        return

    if results:
        print_summary(results)
        if args.format == "json":
            save_json(results, args.output.replace(".csv", ".json"))
        else:
            save_csv(results, args.output)
    else:
        print("[INFO] 无结果")


if __name__ == "__main__":
    main()
