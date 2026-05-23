#!/usr/bin/env python3
"""
Amazon Product Price Monitor
============================
监控 Amazon 商品价格、评分、排名、类目
支持：关键词搜索、ASIN 批量查询、价格历史追踪

⚠️ 仅供个人比价/竞品分析使用
⚠️ 添加延时，避免触发反爬
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
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

BASE_URL = "https://www.amazon.com"
UK_URL = "https://www.amazon.co.uk"


@dataclass
class ProductResult:
    asin: str = ""
    title: str = ""
    price: str = ""
    original_price: str = ""
    currency: str = "USD"
    rating: str = ""
    review_count: str = ""
    best_seller_badge: str = ""
    amazon_choice: str = ""
    category: str = ""
    subcategory: str = ""
    rank: str = ""
    availability: str = ""
    brand: str = ""
    seller: str = ""
    image_url: str = ""
    detail_url: str = ""
    search_keyword: str = ""
    scraped_at: str = ""


def _get_price(product: dict) -> str:
    """提取价格"""
    for key in ["price", "salePrice", "currentPrice", "buyBoxWinnerPrice"]:
        if product.get(key):
            val = product[key]
            if isinstance(val, dict):
                return str(val.get("value", ""))
            return str(val)
    return ""


def _get_optional(product: dict, *keys) -> str:
    for k in keys:
        if product.get(k):
            return str(product[k])
    return ""


def fetch_search_page(keyword: str, page: int = 1, domain: str = "com") -> str | None:
    """获取搜索结果页 HTML"""
    base = BASE_URL if domain == "com" else UK_URL
    page_param = f"&page={page}" if page > 1 else ""
    url = f"{base}/s?k={requests.utils.quote(keyword)}{page_param}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[ERROR] 请求失败: {url} → {e}")
        return None


def parse_search_results(html: str, keyword: str) -> list[ProductResult]:
    """解析搜索结果页"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # 方法1：从 JSON 嵌入数据提取（最可靠）
    scripts = soup.find_all("script")

    for script in scripts:
        text = script.string or ""
        if '"products"' in text or '"result"' in text or '"ASIN"' in text:
            # 尝试提取 JSON
            matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
            for m in matches:
                if '"ASIN"' in m or '"asin"' in m:
                    try:
                        obj = json.loads(m)
                        if obj.get("ASIN") or obj.get("asin"):
                            break
                    except json.JSONDecodeError:
                        pass

    # 方法2：直接解析 HTML（备用）
    items = soup.select("[data-component-type='s-search-result']")

    for item in items:
        p = ProductResult()
        p.search_keyword = keyword
        p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

        # ASIN
        p.asin = item.get("data-asin", "") or item.get("id", "").replace("result_", "")

        # 标题
        title_tag = item.select_one("h2 a span, a.a-color-base.a-text-normal span, [class*='title']")
        if title_tag:
            p.title = title_tag.get_text(strip=True)

        # 价格
        price_tag = item.select_one("[class*='price'] span.a-offscreen, .a-price .a-offscreen, [class*='a-price-whole']")
        if price_tag:
            p.price = price_tag.get_text(strip=True)

        # 原价（划线价）
        orig_tag = item.select_one("[class*='strike'], [class*='list']")
        if orig_tag:
            p.original_price = orig_tag.get_text(strip=True)

        # 评分
        rating_tag = item.select_one("[class*='a-icon-star'] span, [aria-label*='out of']")
        if rating_tag:
            p.rating = rating_tag.get_text(strip=True)

        # 评论数
        review_tag = item.select_one("span.a-size-base.s-underline-text, [class*='review']")
        if review_tag:
            p.review_count = review_tag.get_text(strip=True)

        # 类目标签
        cat_tag = item.select_one("[class*='category']")
        if cat_tag:
            p.category = cat_tag.get_text(strip=True)

        # Amazon Choice
        if item.select_one("[class*='amazon-choice'], [class*='a-badge']"):
            p.amazon_choice = "Yes"

        # Best Seller
        if item.select_one("[class*='best-seller'], [class*='bestseller']"):
            p.best_seller_badge = "Yes"

        # 商品链接
        link_tag = item.select_one("h2 a, a.a-link-normal")
        if link_tag and link_tag.get("href"):
            p.detail_url = (BASE_URL if "com" in str(item) else UK_URL) + link_tag["href"].split("?")[0]

        if p.asin and p.title:
            results.append(p)

    return results


def fetch_product_detail(asin: str, domain: str = "com") -> ProductResult | None:
    """获取单个商品详情页"""
    base = BASE_URL if domain == "com" else UK_URL
    url = f"{base}/dp/{asin}"
    p = ProductResult()
    p.asin = asin
    p.detail_url = url
    p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # 标题
        title_tag = soup.select_one("#productTitle, #title")
        if title_tag:
            p.title = title_tag.get_text(strip=True)

        # 价格
        price_tag = soup.select_one(".a-price .a-offscreen, #priceblock_ourprice, #priceblock_dealprice, .a-price-whole")
        if price_tag:
            p.price = price_tag.get_text(strip=True)

        # 评分
        rating_tag = soup.select_one("#acrPopover .a-icon-alt, [aria-label*='stars']")
        if rating_tag:
            p.rating = rating_tag.get_text(strip=True)

        # 评论数
        review_tag = soup.select_one("#acrCustomerReviewText, [class*='review-count']")
        if review_tag:
            p.review_count = review_tag.get_text(strip=True)

        # 类目排名
        rank_tags = soup.select("#SalesRank .a-text-medium, #detailBulletsWrapper_feature_div li")
        rank_text = " | ".join([t.get_text(strip=True) for t in rank_tags[:3]])
        if rank_text:
            p.rank = rank_text

        # 品牌
        brand_tag = soup.select_one("#bylineInfo, [class*='brand']")
        if brand_tag:
            p.brand = brand_tag.get_text(strip=True)

        # 在售状态
        avail_tag = soup.select_one("#availability span, [class*='availability']")
        if avail_tag:
            p.availability = avail_tag.get_text(strip=True)

        print(f"  ✓ {p.title[:60]} | {p.price}")
        return p

    except requests.RequestException as e:
        print(f"[ERROR] 详情页请求失败: {url} → {e}")
        return None


def search_by_keyword(keyword: str, pages: int = 2, domain: str = "com", delay: float = 3.0) -> list[ProductResult]:
    """搜索关键词，返回多页结果"""
    all_results = []
    for page in range(1, pages + 1):
        print(f"[INFO] 搜索关键词 '{keyword}' 第 {page}/{pages} 页...")
        html = fetch_search_page(keyword, page, domain)
        if html:
            results = parse_search_results(html, keyword)
            all_results.extend(results)
            print(f"  → 本页找到 {len(results)} 条商品")
        time.sleep(delay)
    return all_results


def save_csv(products: list[ProductResult], filename: str):
    if not products:
        print("[INFO] 无数据")
        return
    keys = ["asin", "title", "price", "original_price", "rating", "review_count",
            "category", "rank", "brand", "availability",
            "amazon_choice", "best_seller_badge",
            "detail_url", "search_keyword", "scraped_at"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([asdict(p) for p in products])
    print(f"[✓] 保存 {len(products)} 条 → {filename}")


def save_json(products: list[ProductResult], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in products], f, ensure_ascii=False, indent=2)
    print(f"[✓] 保存 → {filename}")


def main():
    parser = argparse.ArgumentParser(description="Amazon 商品价格监控")
    parser.add_argument("--keyword", help="搜索关键词")
    parser.add_argument("--asin", help="ASIN（可多个，逗号分隔）")
    parser.add_argument("--domain", default="com", choices=["com", "co.uk"],
                        help="Amazon 站点（默认 .com）")
    parser.add_argument("--pages", type=int, default=2, help="搜索结果页数（默认 2）")
    parser.add_argument("--delay", type=float, default=3.0, help="请求间隔秒数（默认 3s）")
    parser.add_argument("-o", "--output", default="amazon_products.csv")
    parser.add_argument("-f", "--format", choices=["csv", "json"], default="csv")
    args = parser.parse_args()

    results = []

    if args.asin:
        asins = [a.strip() for a in args.asin.split(",")]
        print(f"[INFO] 获取 {len(asins)} 个 ASIN 详情...")
        for asin in asins:
            p = fetch_product_detail(asin, args.domain)
            if p:
                results.append(p)
            time.sleep(args.delay)

    elif args.keyword:
        results = search_by_keyword(args.keyword, args.pages, args.domain, args.delay)

    else:
        print("用法示例:")
        print("  # 搜索关键词")
        print("  python amazon_scraper.py --keyword 'wireless headphones'")
        print("  # 搜索多页（英国站）")
        print("  python amazon_scraper.py --keyword 'laptop' --domain co.uk --pages 3")
        print("  # 获取指定 ASIN 详情")
        print("  python amazon_scraper.py --asin B09V3KXJPB,B07XGY4Y1G")
        return

    if results:
        if args.format == "csv":
            save_csv(results, args.output)
        else:
            save_json(results, args.output.replace(".csv", ".json"))


if __name__ == "__main__":
    main()
