#!/usr/bin/env python3
"""
Trip.com Scraper
================
抓取 Trip.com 机票、酒店、景点价格
支持：出发地/目的地/日期参数 / CSV / JSON 导出 / 速率限制

⚠️ 合规提醒：
- 仅供个人旅行规划使用
- 禁止批量采集或商业转售
- Trip.com 页面结构可能变更，请关注输出
"""

import csv
import json
import time
import re
import random
import argparse
import logging
from datetime import datetime
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
BASE_URL = "https://www.trip.com"
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

PROXIES: list[dict] = []  # 可选：添加代理


def _headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": BASE_URL + "/",
        "Origin": BASE_URL,
    }


# ─────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────
@dataclass
class FlightResult:
    airline: str = ""
    flight_no: str = ""
    depart_time: str = ""
    arrive_time: str = ""
    depart_airport: str = ""
    arrive_airport: str = ""
    duration: str = ""
    price: str = ""
    currency: str = "CNY"
    cabin_class: str = ""
    stops: str = ""          # 经停次数
    aircraft_type: str = ""  # 机型
    search_url: str = ""
    searched_at: str = ""


@dataclass
class HotelResult:
    name: str = ""
    star_rating: str = ""      # 星级
    user_rating: str = ""      # 用户评分
    review_count: str = ""
    location: str = ""        # 地标/商圈
    district: str = ""
    price: str = ""
    currency: str = "CNY"
    original_price: str = ""
    discount: str = ""
    amenities: str = ""       # 设施（逗号分隔）
    has_breakfast: str = ""    # 含早餐
    free_cancellation: str = ""  # 免费取消
    image_url: str = ""
    detail_url: str = ""
    searched_at: str = ""


@dataclass
class AttractionResult:
    name: str = ""
    category: str = ""          # 类别
    location: str = ""
    city: str = ""
    rating: str = ""
    review_count: str = ""
    ticket_price: str = ""
    currency: str = "CNY"
    description: str = ""
    opening_hours: str = ""
    image_url: str = ""
    detail_url: str = ""
    searched_at: str = ""


# ─────────────────────────────────────────────
# 通用请求层
# ─────────────────────────────────────────────
def _fetch(url: str, params: dict = None, timeout: int = 15) -> Optional[BeautifulSoup]:
    """通用 GET 请求，含重试"""
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=_headers(), timeout=timeout)
            if resp.status_code == 403 or resp.status_code == 999:
                backoff = random.uniform(5, 15)
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


def _extract_price(text: str) -> str:
    """从文本提取价格数字"""
    if not text:
        return ""
    m = re.search(r"¥?\s*([\d,]+\.?\d*)", text)
    return m.group(1) if m else text.strip()


def _safe_get(d: dict, *keys, default="") -> str:
    """安全获取嵌套字典值"""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, {})
        else:
            return default
    return str(d) if d else default


# ─────────────────────────────────────────────
# 机票搜索
# ─────────────────────────────────────────────
def search_flights(
    depart_code: str,
    arrive_code: str,
    depart_date: str,   # YYYY-MM-DD
    return_date: str = "",
    cabin_class: str = "economy",
    currency: str = "CNY",
) -> list[FlightResult]:
    """
    搜索机票
    depart_code / arrive_code: 机场 IATA 代码，如 LHR, SYD, NRT
    """
    search_url = (
        f"{BASE_URL}/flights/{depart_code}-{arrive_code}/"
        f"{depart_date}?cabin=y&adult=1&child=0&infant=0"
    )
    log.info(f"搜索机票: {depart_code} → {arrive_code} | {depart_date}")
    log.info(f"搜索页: {search_url}")

    results = []
    soup = _fetch(search_url)
    if not soup:
        return results

    now = datetime.now().isoformat(timespec="seconds")

    # ── 方法 1: 从 JSON script 提取 ────────────────
    scripts = soup.find_all("script")
    for script in scripts:
        text = (script.string or "")
        if "flightList" not in text and "flightNo" not in text:
            continue

        # 尝试匹配 flightList JSON 数组
        for match in re.finditer(r'"flightList"\s*:\s*(\[.*?\])\s*[,}]', text, re.DOTALL):
            try:
                flight_data = json.loads(match.group(1))
                if isinstance(flight_data, list):
                    for f in flight_data[:20]:
                        r = FlightResult(search_url=search_url, searched_at=now, currency=currency)
                        r.airline = f.get("airlineName", "") or _safe_get(f, "airline", "name")
                        r.flight_no = f.get("flightNo", "")
                        r.depart_time = f.get("departureDateTime", "")
                        r.arrive_time = f.get("arrivalDateTime", "")
                        r.depart_airport = f.get("departureAirport", "") or _safe_get(f, "departureAirport", "name")
                        r.arrive_airport = f.get("arrivalAirport", "") or _safe_get(f, "arrivalAirport", "name")
                        r.duration = f.get("duration", "")
                        r.stops = str(f.get("stops", "0"))
                        r.cabin_class = cabin_class
                        price = f.get("price") or f.get("priceInfo", {}).get("price")
                        r.price = str(price) if price else ""
                        results.append(r)
            except json.JSONDecodeError:
                pass

    # ── 方法 2: HTML 解析（备用）─────────────────
    if not results:
        log.info("JSON 解析为空，尝试 HTML 备用解析...")
        cards = soup.select(
            "[class*='flight'], [class*='cabin'], "
            "[data-component*='flight'], .flight-card"
        )
        for card in cards[:15]:
            r = FlightResult(search_url=search_url, searched_at=now, currency=currency)
            r.cabin_class = cabin_class

            # 航司
            airline_tag = card.select_one("[class*='airline'], [class*='logo'] img")
            if airline_tag:
                r.airline = (airline_tag.get("alt") or airline_tag.get_text(strip=True))[:50]

            # 航班号
            fn_tag = card.select_one("[class*='flight-no'], [class*='flightNo']")
            if fn_tag:
                r.flight_no = fn_tag.get_text(strip=True)

            # 时间
            dep_tag = card.select_one("[class*='depart'], [class*='dep-time']")
            arr_tag = card.select_one("[class*='arrive'], [class*='arr-time']")
            if dep_tag:
                r.depart_time = dep_tag.get_text(strip=True)
            if arr_tag:
                r.arrive_time = arr_tag.get_text(strip=True)

            # 价格
            price_tag = card.select_one("[class*='price'], [class*='money']")
            if price_tag:
                r.price = _extract_price(price_tag.get_text())

            if r.airline or r.flight_no or r.price:
                results.append(r)

    log.info(f"✓ 找到 {len(results)} 条航班")
    return results


# ─────────────────────────────────────────────
# 酒店搜索
# ─────────────────────────────────────────────
def search_hotels(
    city_pinyin: str,
    keyword: str = "",
    checkin: str = "",
    checkout: str = "",
    currency: str = "CNY",
) -> list[HotelResult]:
    """
    搜索酒店
    city_pinyin: 城市拼音，如 shanghai, london, paris
    """
    params = {}
    if keyword:
        params["kwd"] = keyword
    if checkin:
        params["checkin"] = checkin
    if checkout:
        params["checkout"] = checkout

    search_url = f"{BASE_URL}/hotels/{city_pinyin}"
    if params:
        search_url += "?" + "&".join(f"{k}={v}" for k, v in params.items())

    log.info(f"搜索酒店: {city_pinyin} {keyword}")
    log.info(f"搜索页: {search_url}")

    results = []
    soup = _fetch(search_url)
    if not soup:
        return results

    now = datetime.now().isoformat(timespec="seconds")

    # ── 方法 1: JSON script ─────────────────────
    scripts = soup.find_all("script")
    for script in scripts:
        text = (script.string or "")
        if "hotelList" not in text and "hotelName" not in text:
            continue

        for match in re.finditer(r'"hotelList"\s*:\s*(\[.*?\])\s*[,}]', text, re.DOTALL):
            try:
                hotel_data = json.loads(match.group(1))
                if isinstance(hotel_data, list):
                    for h in hotel_data[:20]:
                        r = HotelResult(searched_at=now, currency=currency)
                        r.name = h.get("hotelName", "")
                        r.star_rating = str(h.get("starRating", ""))
                        r.user_rating = str(h.get("rating", ""))
                        r.review_count = str(h.get("reviewCount", ""))
                        r.location = h.get("locationName", "")
                        r.district = h.get("districtName", "")
                        price = h.get("price")
                        r.price = str(price) if price else ""
                        r.original_price = str(h.get("originalPrice", ""))
                        r.discount = h.get("discountText", "")
                        facilities = h.get("facilityList") or []
                        r.amenities = ",".join(str(f) for f in facilities[:8])
                        r.has_breakfast = "Yes" if h.get("hasBreakfast") else "No"
                        r.free_cancellation = "Yes" if h.get("freeCancellation") else "No"
                        img = h.get("imageUrl") or h.get("hotelImage", [{}])[0].get("url", "")
                        r.image_url = img
                        du = h.get("detailUrl", "")
                        r.detail_url = BASE_URL + du if not du.startswith("http") else du
                        if r.name or r.price:
                            results.append(r)
            except json.JSONDecodeError:
                pass

    # ── 方法 2: HTML 备用解析 ────────────────────
    if not results:
        log.info("JSON 解析为空，尝试 HTML 备用解析...")
        cards = soup.select(
            "[class*='hotel'], [class*='list-item'], "
            "[class*='poi-card'], .hotel-card"
        )
        for card in cards[:15]:
            r = HotelResult(searched_at=now, currency=currency)

            name_tag = card.select_one("h3, [class*='name'], [class*='title']")
            if name_tag:
                r.name = name_tag.get_text(strip=True)

            price_tag = card.select_one("[class*='price'], [class*='money'], strong")
            if price_tag:
                r.price = _extract_price(price_tag.get_text())

            rating_tag = card.select_one("[class*='rating'], [class*='score']")
            if rating_tag:
                r.user_rating = rating_tag.get_text(strip=True)

            if r.name:
                results.append(r)

    log.info(f"✓ 找到 {len(results)} 家酒店")
    return results


# ─────────────────────────────────────────────
# 景点搜索
# ─────────────────────────────────────────────
def search_attractions(
    city_pinyin: str,
    keyword: str = "",
    city_name: str = "",
    currency: str = "CNY",
) -> list[AttractionResult]:
    """
    搜索景点
    city_pinyin: 城市拼音
    keyword: 可选关键词
    """
    params = {}
    if keyword:
        params["kwd"] = keyword
    search_url = f"{BASE_URL}/attractions/{city_pinyin}"
    if params:
        search_url += "?" + "&".join(f"{k}={v}" for k, v in params.items())

    log.info(f"搜索景点: {city_pinyin} {keyword}")
    log.info(f"搜索页: {search_url}")

    results = []
    soup = _fetch(search_url)
    if not soup:
        return results

    now = datetime.now().isoformat(timespec="seconds")

    # ── JSON script ───────────────────────────
    scripts = soup.find_all("script")
    for script in scripts:
        text = (script.string or "")
        if "poiList" not in text and "attraction" not in text.lower():
            continue

        for match in re.finditer(r'"poiList"\s*:\s*(\[.*?\])\s*[,}]', text, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    for a in data[:20]:
                        r = AttractionResult(searched_at=now, currency=currency)
                        r.name = a.get("name", "")
                        r.category = a.get("categoryName", "")
                        r.location = a.get("address", "")
                        r.city = city_name or city_pinyin
                        r.rating = str(a.get("rating", ""))
                        r.review_count = str(a.get("reviewCount", ""))
                        r.ticket_price = str(a.get("price", ""))
                        r.description = a.get("description", "")[:200]
                        r.opening_hours = a.get("openTime", "")
                        img = a.get("imageUrl") or ""
                        r.image_url = img
                        du = a.get("detailUrl", "")
                        r.detail_url = BASE_URL + du if not du.startswith("http") else du
                        if r.name:
                            results.append(r)
            except json.JSONDecodeError:
                pass

    if not results:
        log.info("JSON 解析为空，尝试 HTML 备用解析...")
        cards = soup.select("[class*='poi'], [class*='attraction'], [class*='sight']")
        for card in cards[:15]:
            r = AttractionResult(searched_at=now, currency=currency)
            name_tag = card.select_one("h3, [class*='name'], a")
            if name_tag:
                r.name = name_tag.get_text(strip=True)
            if r.name:
                results.append(r)

    log.info(f"✓ 找到 {len(results)} 个景点")
    return results


# ─────────────────────────────────────────────
# 保存结果
# ─────────────────────────────────────────────
def save_csv(items: list, filename: str):
    if not items:
        log.info("无数据可保存")
        return
    keys = list(asdict(items[0]).keys())
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([asdict(i) for i in items])
    log.info(f"✓ 保存 {len(items)} 条 → {filename}")


def save_json(items: list, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump([asdict(i) for i in items], f, ensure_ascii=False, indent=2)
    log.info(f"✓ 保存 JSON → {filename}")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Trip.com 爬虫（机票 / 酒店 / 景点）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例:
  # 搜索机票
  python trip_scraper.py --type flight --from LHR --to NRT --date 2025-06-15

  # 搜索酒店
  python trip_scraper.py --type hotel --city london --checkin 2025-06-15 --checkout 2025-06-18

  # 景点搜索
  python trip_scraper.py --type attraction --city paris --keyword "Eiffel Tower"

  # 保存 JSON
  python trip_scraper.py --type flight --from SYD --to SIN --date 2025-07-01 -f json -o flights.json

城市拼音参考: london / paris / tokyo / shanghai / sydney / new-york
        """,
    )
    parser.add_argument("--type", choices=["flight", "hotel", "attraction"], required=True)
    parser.add_argument("--from", dest="depart", help="出发机场 IATA 代码（如 LHR）")
    parser.add_argument("--to", dest="arrive", help="到达机场 IATA 代码")
    parser.add_argument("--city", help="城市拼音（hotel/attraction 用）")
    parser.add_argument("--date", help="出发日期 YYYY-MM-DD（flight 用）")
    parser.add_argument("--checkin", help="入住日期 YYYY-MM-DD（hotel 用）")
    parser.add_argument("--checkout", help="退房日期 YYYY-MM-DD（hotel 用）")
    parser.add_argument("--keyword", help="关键词（可选）")
    parser.add_argument("--currency", default="CNY", help="货币（默认 CNY）")
    parser.add_argument("-o", "--output", default="output.csv")
    parser.add_argument("-f", "--format", choices=["csv", "json"], default="csv")
    args = parser.parse_args()

    results = []

    if args.type == "flight":
        if not (args.depart and args.arrive and args.date):
            log.error("flight 模式需要: --from --to --date")
            return
        results = search_flights(args.depart, args.arrive, args.date, currency=args.currency)

    elif args.type == "hotel":
        if not args.city:
            log.error("hotel 模式需要: --city")
            return
        results = search_hotels(args.city, args.keyword, args.checkin, args.checkout, args.currency)

    elif args.type == "attraction":
        if not args.city:
            log.error("attraction 模式需要: --city")
            return
        results = search_attractions(args.city, args.keyword, currency=args.currency)

    if results:
        if args.format == "csv":
            save_csv(results, args.output)
        else:
            save_json(results, args.output)
    else:
        log.warning("无结果 — Trip.com 页面结构可能已变更，或需要登录")


if __name__ == "__main__":
    main()
