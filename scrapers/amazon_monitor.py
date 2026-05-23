#!/usr/bin/env python3
"""
Amazon Product Price Monitor
===========================
监控 Amazon 商品价格、评分、排名、类目
支持：关键词搜索 / ASIN 批量查询 / 价格历史追踪 / 速率限制 / UA 轮换

⚠️ 合规提醒：
- 仅供个人比价 / 竞品分析使用
- 遵守 robots.txt 和 Amazon 使用条款
- 添加延时，避免触发反爬
"""

import os
import csv
import json
import time
import re
import random
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# 日志配置
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────
BASE_URL = "https://www.amazon.com"
UK_URL = "https://www.amazon.co.uk"
DE_URL = "https://www.amazon.de"

# User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

# 代理配置（可选）
PROXIES: list[dict] = []


def _headers() -> dict:
    """每次请求随机 UA"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }


def _proxy() -> Optional[dict]:
    return random.choice(PROXIES) if PROXIES else None


# ─────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────
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
    domain: str = ""
    scraped_at: str = ""


@dataclass
class PriceHistoryEntry:
    """单条价格历史记录"""
    asin: str = ""
    title: str = ""
    price: str = ""
    currency: str = ""
    rating: str = ""
    review_count: str = ""
    availability: str = ""
    timestamp: str = ""


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def _url_for(domain: str, path: str) -> str:
    """返回指定站点的完整 URL"""
    base = {"com": BASE_URL, "co.uk": UK_URL, "de": DE_URL}.get(domain, BASE_URL)
    return f"{base}{path}"


def _extract_number(text: str) -> Optional[float]:
    """从价格文本提取数字"""
    if not text:
        return None
    m = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
    return float(m.group().replace(",", "")) if m else None


def _domain_currency(domain: str) -> str:
    return {"co.uk": "GBP", "de": "EUR"}.get(domain, "USD")


# ─────────────────────────────────────────────
# 请求层
# ─────────────────────────────────────────────
def _fetch(url: str, timeout: int = 20) -> Optional[BeautifulSoup]:
    """通用 GET 请求，自动重试"""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=_headers(), proxies=_proxy(), timeout=timeout)
            if resp.status_code == 503 or resp.status_code == 999:
                backoff = random.uniform(5, 20)
                log.warning(f"状态码 {resp.status_code}，{backoff:.0f}s 后重试...")
                time.sleep(backoff)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            if attempt < 2:
                wait = (2 ** attempt) + random.uniform(1, 3)
                log.warning(f"[尝试 {attempt+1}] {e}，{wait:.1f}s 后重试...")
                time.sleep(wait)
            else:
                log.error(f"[最终失败] {url} → {e}")
    return None


# ─────────────────────────────────────────────
# 搜索结果页
# ─────────────────────────────────────────────
def fetch_search_page(keyword: str, page: int = 1, domain: str = "com") -> Optional[str]:
    base = _url_for(domain, "")
    page_param = f"&page={page}" if page > 1 else ""
    url = f"{base}/s?k={requests.utils.quote(keyword)}{page_param}"
    try:
        resp = requests.get(url, headers=_headers(), proxies=_proxy(), timeout=20)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        log.error(f"搜索页请求失败: {url} → {e}")
        return None


def parse_search_results(html: str, keyword: str, domain: str = "com") -> list[ProductResult]:
    """
    解析 Amazon 搜索结果页
    同时尝试从 <script> JSON 数据和 HTML 结构提取
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    currency = _domain_currency(domain)
    base = _url_for(domain, "")

    # ① 从 script 标签提取 JSON（更可靠）
    scripts = soup.find_all("script")
    for script in scripts:
        text = (script.string or "")
        if '"products"' not in text and '"result"' not in text:
            continue
        # 找 ASIN 相关 JSON 块
        for m in re.finditer(r'"asin"\s*:\s*"([^"]+)"', text):
            asin = m.group(1)
            if asin and asin not in [r.asin for r in results]:
                p = ProductResult(asin=asin, search_keyword=keyword, domain=domain,
                                   currency=currency, scraped_at=datetime.now().isoformat(timespec="seconds"))
                results.append(p)

    # ② HTML 解析（主要方法）
    items = soup.select("[data-component-type='s-search-result']")

    for item in items:
        p = ProductResult(
            search_keyword=keyword,
            domain=domain,
            currency=currency,
            scraped_at=datetime.now().isoformat(timespec="seconds"),
        )

        # ASIN
        p.asin = item.get("data-asin") or ""
        if not p.asin:
            h_id = item.get("id", "")
            p.asin = re.sub(r"^result_", "", h_id)

        # 标题
        for sel in ("h2 a span", "a.a-color-base.a-text-normal span",
                    "[class*='title'] span", "span.a-size-medium"):
            tag = item.select_one(sel)
            if tag and tag.get_text(strip=True):
                p.title = tag.get_text(strip=True)
                break

        # 价格（多个选择器）
        for sel in (
            "[class*='price'] span.a-offscreen",
            ".a-price .a-offscreen",
            "[class*='a-price-whole']",
            "[class*='puis-price'] span",
        ):
            tag = item.select_one(sel)
            if tag:
                p.price = tag.get_text(strip=True)
                break

        # 原价（划线价）
        orig_tag = item.select_one(
            "[class*='strike'], [class*='list'], span.a-text-price span.a-offscreen"
        )
        if orig_tag:
            p.original_price = orig_tag.get_text(strip=True)

        # 评分
        for sel in ("[class*='a-icon-star'] span", "[aria-label*='out of']"):
            tag = item.select_one(sel)
            if tag:
                p.rating = tag.get_text(strip=True)
                break

        # 评论数
        rev_tag = item.select_one("span.a-size-base.s-underline-text")
        if not rev_tag:
            rev_tag = item.select_one("[class*='review']")
        if rev_tag:
            p.review_count = rev_tag.get_text(strip=True)

        # Amazon Choice
        if item.select_one("[class*='amazon-choice'], [class*='a-badge']"):
            p.amazon_choice = "Yes"

        # Best Seller
        if item.select_one("[class*='best-seller'], [class*='bestseller']"):
            p.best_seller_badge = "Yes"

        # 商品链接
        link_tag = item.select_one("h2 a, a.a-link-normal")
        if link_tag and link_tag.get("href"):
            p.detail_url = base + link_tag["href"].split("?")[0]

        # 去重：已有同 ASIN 且有标题的跳过
        if p.asin and p.title:
            if not any(r.asin == p.asin and r.title for r in results):
                results.append(p)

    return results


# ─────────────────────────────────────────────
# 商品详情页
# ─────────────────────────────────────────────
def fetch_product_detail(asin: str, domain: str = "com") -> Optional[ProductResult]:
    url = _url_for(domain, f"/dp/{asin}")
    currency = _domain_currency(domain)
    p = ProductResult(asin=asin, domain=domain, currency=currency,
                      detail_url=url, scraped_at=datetime.now().isoformat(timespec="seconds"))

    soup = _fetch(url)
    if not soup:
        return None

    # 标题
    for sel in ("#productTitle", "#title", "h1.product-title-word-break"):
        tag = soup.select_one(sel)
        if tag:
            p.title = tag.get_text(strip=True)
            break

    # 价格
    for sel in (
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#priceblock_saleprice",
        ".a-price .a-offscreen",
        "[data-a-color='price'] .a-offscreen",
        "#corePrice_feature_div .a-offscreen",
    ):
        tag = soup.select_one(sel)
        if tag:
            p.price = tag.get_text(strip=True)
            break

    # 原价（划线）
    for sel in ("#listPrice", "#priceblock_listprice", ".a-text-price .a-offscreen"):
        tag = soup.select_one(sel)
        if tag:
            p.original_price = tag.get_text(strip=True)
            break

    # 评分
    for sel in ("#acrPopover .a-icon-alt", "[aria-label*='stars']", ".a-icon-alt"):
        tag = soup.select_one(sel)
        if tag:
            p.rating = tag.get_text(strip=True)
            break

    # 评论数
    for sel in ("#acrCustomerReviewText", "[class*='review-count']", "a[href='#customerReviews']"):
        tag = soup.select_one(sel)
        if tag:
            p.review_count = tag.get_text(strip=True)
            break

    # 类目排名
    rank_parts = []
    for sel in ("#SalesRank", "#detailBulletsWrapper_feature_div",
                "[data-feature-name='salesRank']"):
        tag = soup.select_one(sel)
        if tag:
            texts = tag.get_text(strip=True)
            rank_parts.append(texts[:200])
    p.rank = " | ".join(rank_parts)[:500]

    # 品牌
    for sel in ("#bylineInfo", "[class*='brand']", "[class*='Brand']"):
        tag = soup.select_one(sel)
        if tag:
            p.brand = tag.get_text(strip=True)
            break

    # 在售状态
    for sel in ("#availability span", "[class*='availability']", ".a-color-success"):
        tag = soup.select_one(sel)
        if tag:
            p.availability = tag.get_text(strip=True)
            break

    # 主图 URL
    img_tag = soup.select_one("#landingImage, #imgBlkFront, [data-old-hirescover]")
    if img_tag:
        p.image_url = img_tag.get("src") or img_tag.get("data-a-dynamic-image") or ""

    log.info(f"  ✓ {p.title[:60]} | {p.price} {currency}")
    return p


# ─────────────────────────────────────────────
# 价格历史
# ─────────────────────────────────────────────
HISTORY_DIR = Path("price_history")
HISTORY_DIR.mkdir(exist_ok=True)


def _history_path(asin: str, domain: str) -> Path:
    return HISTORY_DIR / f"{domain}_{asin}.csv"


def load_price_history(asin: str, domain: str) -> list[PriceHistoryEntry]:
    """从 CSV 读取该商品的历史价格"""
    path = _history_path(asin, domain)
    if not path.exists():
        return []
    entries = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            entries.append(PriceHistoryEntry(**row))
    return entries


def append_price_history(product: ProductResult):
    """追加当前价格到历史 CSV"""
    path = _history_path(product.asin, product.domain)
    entry = PriceHistoryEntry(
        asin=product.asin,
        title=product.title[:200],
        price=product.price,
        currency=product.currency,
        rating=product.rating,
        review_count=product.review_count,
        availability=product.availability,
        timestamp=datetime.now().isoformat(timespec="seconds"),
    )
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(entry).keys()))
        if is_new:
            writer.writeheader()
        writer.writerow(asdict(entry))
    log.info(f"  📊 价格历史已追加 → {path.name}")


def print_price_history(asin: str, domain: str):
    """打印价格变动趋势"""
    history = load_price_history(asin, domain)
    if not history:
        log.info(f"暂无历史数据: {asin}")
        return

    print(f"\n  价格历史 ({asin}):")
    print(f"  {'时间':<25} {'价格':<12} {'评分':<10} {'状态'}")
    print("  " + "-" * 62)
    for entry in history[-10:]:
        print(f"  {entry.timestamp:<25} {entry.price:<12} {entry.rating:<10} {entry.availability[:20]}")

    prices = [_extract_number(e.price) for e in history if _extract_number(e.price)]
    if prices:
        print(f"\n  📈 均价: {min(prices):.2f} | 最高: {max(prices):.2f} | 最新: {prices[-1]:.2f}")


# ─────────────────────────────────────────────
# 搜索入口
# ─────────────────────────────────────────────
def search_by_keyword(
    keyword: str,
    pages: int = 2,
    domain: str = "com",
    delay: float = 3.0,
) -> list[ProductResult]:
    all_results = []
    for page in range(1, pages + 1):
        log.info(f"搜索 '{keyword}' 第 {page}/{pages} 页 ({domain})...")
        html = fetch_search_page(keyword, page, domain)
        if html:
            results = parse_search_results(html, keyword, domain)
            all_results.extend(results)
            log.info(f"  → 本页 {len(results)} 条商品")
        jitter = random.uniform(-0.5, 0.5)
        time.sleep(max(1.0, delay + jitter))
    return all_results


# ─────────────────────────────────────────────
# 保存
# ─────────────────────────────────────────────
def save_csv(products: list[ProductResult], filename: str):
    if not products:
        log.info("无数据可保存")
        return
    keys = [
        "asin", "title", "price", "original_price", "rating", "review_count",
        "category", "rank", "brand", "availability",
        "amazon_choice", "best_seller_badge",
        "detail_url", "search_keyword", "domain", "scraped_at",
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([asdict(p) for p in products])
    log.info(f"✓ 保存 {len(products)} 条 → {filename}")


def save_json(products: list[ProductResult], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in products], f, ensure_ascii=False, indent=2)
    log.info(f"✓ 保存 JSON → {filename}")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Amazon 商品价格监控（含历史价格追踪）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例:
  # 关键词搜索（美国站，2页）
  python amazon_monitor.py --keyword 'wireless headphones'

  # 英国站，3页，保存 CSV
  python amazon_monitor.py --keyword 'laptop' --domain co.uk --pages 3

  # ASIN 批量查询并追踪价格历史
  python amazon_monitor.py --asin B09V3KXJPB,B07XGY4Y1G --track

  # 查看历史价格
  python amazon_monitor.py --history B09V3KXJPB --domain com

  # 搜索 + 同时记录价格历史
  python amazon_monitor.py --keyword 'nintendo switch' --track
        """,
    )
    parser.add_argument("--keyword", help="搜索关键词")
    parser.add_argument("--asin", help="ASIN（可多个，逗号分隔）")
    parser.add_argument("--domain", default="com", choices=["com", "co.uk", "de"],
                        help="Amazon 站点（默认 .com）")
    parser.add_argument("--pages", type=int, default=2, help="搜索结果页数（默认 2）")
    parser.add_argument("--delay", type=float, default=3.0, help="请求间隔秒数（默认 3s）")
    parser.add_argument("-o", "--output", default="amazon_products.csv")
    parser.add_argument("-f", "--format", choices=["csv", "json"], default="csv")

    # 价格历史功能
    parser.add_argument("--track", action="store_true",
                        help="抓取后记录价格到历史 CSV")
    parser.add_argument("--history", metavar="ASIN",
                        help="打印指定 ASIN 的历史价格趋势（不发起新抓取）")
    parser.add_argument("--monitor", action="store_true",
                        help="持续监控模式：每 --interval 分钟抓取一次")

    args = parser.parse_args()

    # ── 历史价格查询 ───────────────────────────
    if args.history:
        print_price_history(args.history, args.domain)
        return

    # ── 持续监控模式 ──────────────────────────
    if args.monitor:
        interval = args.delay * 60  # delay 参数兼作分钟数
        log.info(f"启动监控模式，间隔 {interval / 60:.0f} 分钟（Ctrl+C 停止）")
        count = 0
        while True:
            count += 1
            log.info(f"\n=== 第 {count} 次监控轮次 ===")
            if args.asin:
                asins = [a.strip() for a in args.asin.split(",")]
                for asin in asins:
                    p = fetch_product_detail(asin, args.domain)
                    if p:
                        append_price_history(p)
                    time.sleep(args.delay)
            elif args.keyword:
                results = search_by_keyword(args.keyword, args.pages, args.domain, args.delay)
                for p in results:
                    append_price_history(p)
            log.info(f"本轮完成，等待 {interval / 60:.0f} 分钟后继续...")
            time.sleep(interval)
        return

    results = []

    if args.asin:
        asins = [a.strip() for a in args.asin.split(",")]
        log.info(f"获取 {len(asins)} 个 ASIN 详情...")
        for asin in asins:
            p = fetch_product_detail(asin, args.domain)
            if p:
                results.append(p)
                if args.track:
                    append_price_history(p)
            jitter = random.uniform(-0.5, 0.5)
            time.sleep(max(1.0, args.delay + jitter))

    elif args.keyword:
        results = search_by_keyword(args.keyword, args.pages, args.domain, args.delay)
        if args.track:
            log.info(f"记录 {len(results)} 个商品的价格历史...")
            for p in results:
                append_price_history(p)

    else:
        log.error("请提供 --keyword 或 --asin 参数")
        parser.print_help()
        return

    if results:
        if args.format == "csv":
            save_csv(results, args.output)
        else:
            save_json(results, args.output.replace(".csv", ".json"))


if __name__ == "__main__":
    main()
