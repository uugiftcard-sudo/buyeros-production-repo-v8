#!/usr/bin/env python3
"""
eBay Seller & Product Scraper
=============================
抓取 eBay 公开卖家信息和商品数据
支持：关键词搜索、卖家主页、店铺信息

⚠️ 仅供个人使用，禁止批量采集用于商业销售
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
}

BASE_URL = "https://www.ebay.com"


@dataclass
class SellerResult:
    seller_id: str = ""
    seller_name: str = ""
    feedback_score: str = ""
    feedback_percent: str = ""
    positive_feedback: str = ""
    neutral_feedback: str = ""
    negative_feedback: str = ""
    member_since: str = ""
    location: str = ""
    business: bool = False
    top_rated: bool = False
    registration_id: str = ""
    detail_url: str = ""


@dataclass
class ItemResult:
    item_id: str = ""
    title: str = ""
    price: str = ""
    currency: str = "USD"
    condition: str = ""
    listing_type: str = ""
    seller_id: str = ""
    seller_rating: str = ""
    sold_count: str = ""
    watching_count: str = ""
    bids_count: str = ""
    location: str = ""
    returns: str = ""
    shipping: str = ""
    category: str = ""
    category_id: str = ""
    image_url: str = ""
    detail_url: str = ""
    end_time: str = ""
    search_keyword: str = ""
    scraped_at: str = ""


# ────────────────────────────────────────────────
# 搜索商品
# ────────────────────────────────────────────────
def search_items(
    keyword: str,
    category: str = "",
    condition: str = "",
    max_price: str = "",
    min_price: str = "",
    listing_type: str = "all",
    sort: str = "best_match",
    limit: int = 50,
    delay: float = 3.0,
) -> list[ItemResult]:
    """搜索 eBay 商品"""
    # eBay Browse API（推荐，无需登录）
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    params = {
        "q": keyword,
        "limit": min(limit, 100),
        "sort": sort,
    }
    if category:
        params["category_ids"] = category
    if max_price:
        params["max_price"] = max_price
    if min_price:
        params["min_price"] = min_price

    headers = {
        "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=,affiliateReferenceId=,contextualLocation=,usageType=SEARCH",
        "Accept": "application/json",
    }

    results = []
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("itemSummaries", [])
            for item in items:
                r = ItemResult()
                r.search_keyword = keyword
                r.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                r.item_id = item.get("itemId", "")
                r.title = item.get("title", "")
                price = item.get("price", {})
                r.price = f"{price.get('value', '')} {price.get('currency', 'USD')}"
                r.currency = price.get("currency", "USD")
                r.condition = item.get("condition", "")
                r.condition = item.get("condition", "")
                r.listing_type = item.get("listingType", "")
                r.seller_id = item.get("seller", {}).get("username", "")
                r.seller_rating = item.get("seller", {}).get("feedbackScore", "")
                r.sold_count = item.get("itemEndDate", "")  # 实际 sold count 需单独 API
                r.location = item.get("location", "")
                r.category = item.get("categories", [{}])[0].get("categoryName", "") if item.get("categories") else ""
                r.image_url = item.get("image", {}).get("imageUrl", "") if isinstance(item.get("image"), dict) else ""
                r.detail_url = item.get("itemWebUrl", "")
                results.append(r)
            print(f"[✓] API 找到 {len(results)} 条商品 ← {keyword}")
            return results

    except requests.RequestException:
        pass

    # 备用：HTML 抓取
    print("[INFO] API 不可用，切换 HTML 解析...")
    return _search_items_html(keyword, limit, delay)


def _search_items_html(keyword: str, limit: int, delay: float) -> list[ItemResult]:
    """HTML 备用解析"""
    search_url = f"{BASE_URL}/sch/i.html?_nkw={requests.utils.quote(keyword)}&_ipg=60"
    results = []

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("[class*='s-item']")

        for item in items[:limit]:
            r = ItemResult()
            r.search_keyword = keyword
            r.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

            title_tag = item.select_one("[class*='s-item__title']")
            if title_tag:
                r.title = title_tag.get_text(strip=True)

            price_tag = item.select_one("[class*='s-item__price']")
            if price_tag:
                r.price = price_tag.get_text(strip=True)

            cond_tag = item.select_one("[class*='s-item__subtitle']")
            if cond_tag:
                r.condition = cond_tag.get_text(strip=True)

            link_tag = item.select_one("a.s-item__link")
            if link_tag and link_tag.get("href"):
                href = link_tag["href"]
                r.detail_url = href
                match = re.search(r'/(\d+)\?', href)
                if match:
                    r.item_id = match.group(1)

            seller_tag = item.select_one("[class*='s-item__seller']")
            if seller_tag:
                r.seller_id = seller_tag.get_text(strip=True).replace("Seller:", "").strip()

            results.append(r)
            time.sleep(delay)

        print(f"[✓] HTML 解析找到 {len(results)} 条商品")
        return results

    except requests.RequestException as e:
        print(f"[ERROR] 请求失败: {e}")
        return []


# ────────────────────────────────────────────────
# 卖家信息
# ────────────────────────────────────────────────
def fetch_seller(seller_id: str) -> SellerResult | None:
    """获取卖家公开信息"""
    url = f"{BASE_URL}/usr/{seller_id}"
    s = SellerResult()
    s.seller_id = seller_id
    s.detail_url = url

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # 卖家名称
        name_tag = soup.select_one("[class*='user-name'], [class*='member-name'] h1")
        if name_tag:
            s.seller_name = name_tag.get_text(strip=True)

        # 反馈分数
        score_tag = soup.select_one("[class*='feedback-score'], [class*='ux-icon-section']")
        if score_tag:
            s.feedback_score = score_tag.get_text(strip=True)

        # 好评率
        pct_tag = soup.select_one("[class*='feedback-percentage'], [class*='percentage']")
        if pct_tag:
            s.feedback_percent = pct_tag.get_text(strip=True)

        # 注册时间
        since_tag = soup.select_one("[class*='member-since'], [class*='reg-date']")
        if since_tag:
            s.member_since = since_tag.get_text(strip=True)

        # 位置
        loc_tag = soup.select_one("[class*='user-location'], [class*='location']")
        if loc_tag:
            s.location = loc_tag.get_text(strip=True)

        # Top Rated
        s.top_rated = bool(soup.select_one("[class*='top-rated']"))

        print(f"  ✓ {s.seller_id} | 评分: {s.feedback_score} | 位置: {s.location}")
        return s

    except requests.RequestException as e:
        print(f"[ERROR] 卖家页请求失败: {e}")
        return None


# ────────────────────────────────────────────────
# 保存
# ────────────────────────────────────────────────
def save_csv(items, filename: str):
    if not items:
        print("[INFO] 无数据")
        return
    keys = list(asdict(items[0]).keys())
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([asdict(i) for i in items])
    print(f"[✓] 保存 {len(items)} 条 → {filename}")


def save_json(items, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump([asdict(i) for i in items], f, ensure_ascii=False, indent=2)
    print(f"[✓] 保存 → {filename}")


# ────────────────────────────────────────────────
# 主程序
# ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="eBay 爬虫")
    parser.add_argument("--search", help="搜索关键词")
    parser.add_argument("--seller", help="卖家 ID（可多个，逗号分隔）")
    parser.add_argument("--category", help="分类 ID（可选）")
    parser.add_argument("--condition", help="商品状况（如 new, used）")
    parser.add_argument("--max-price", help="最高价格")
    parser.add_argument("--min-price", help="最低价格")
    parser.add_argument("--sort", default="best_match",
                        choices=["best_match", "price_asc", "price_desc", "newly_listed"],
                        help="排序方式")
    parser.add_argument("--limit", type=int, default=50, help="最大结果数")
    parser.add_argument("--delay", type=float, default=3.0, help="请求间隔秒数")
    parser.add_argument("-o", "--output", default="ebay_results.csv")
    parser.add_argument("-f", "--format", choices=["csv", "json"], default="csv")
    args = parser.parse_args()

    results = []

    if args.seller:
        seller_ids = [s.strip() for s in args.seller.split(",")]
        print(f"[INFO] 获取 {len(seller_ids)} 个卖家信息...")
        for sid in seller_ids:
            s = fetch_seller(sid)
            if s:
                results.append(s)
            time.sleep(args.delay)
        if results:
            out = args.output
            if args.format == "json":
                save_json(results, out.replace(".csv", ".json"))
            else:
                save_csv(results, out)

    elif args.search:
        items = search_items(
            args.search, args.category, args.condition,
            args.max_price, args.min_price,
            sort=args.sort, limit=args.limit, delay=args.delay
        )
        if items:
            out = args.output
            if args.format == "json":
                save_json(items, out.replace(".csv", ".json"))
            else:
                save_csv(items, out)
        else:
            print("[INFO] 无结果")

    else:
        print("""
eBay Scraper — 用法示例
=============================

# 搜索商品
python ebay_scraper.py --search "iphone 15 pro"

# 搜索并限制价格范围（英国站）
python ebay_scraper.py --search "macbook" --max-price 1500 --sort price_asc

# 搜索并指定商品状况
python ebay_scraper.py --search "nintendo switch" --condition used

# 获取卖家信息
python ebay_scraper.py --seller johndoe_uk,janeshop123

# 批量卖家 + 输出 JSON
python ebay_scraper.py --seller seller1,seller2,seller3 -f json
""")


if __name__ == "__main__":
    main()
