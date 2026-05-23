#!/usr/bin/env python3
"""
LinkedIn Public Profile Scraper
===============================
抓取 LinkedIn 公开页面数据（姓名、职位、公司、行业、地区）
支持：单页抓取 / 批量 URL 列表 / 关键词搜索 / 代理轮换 / 速率限制

⚠️ 免责声明：
- 仅抓取用户主动公开的信息
- 禁止用于骚扰、未经同意的营销
- 请遵守 LinkedIn User Agreement 和 robots.txt
- 建议添加 random delay 避免触发反爬
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import re
import random
import argparse
import logging
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import urljoin, urlparse

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
# User-Agent 池 — 每次请求随机选择一个
# ─────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# ─────────────────────────────────────────────
# 代理配置区 — 格式: [{"http": "http://user:pass@host:port"}, ...]
# 无代理时保持空列表 []
# ─────────────────────────────────────────────
PROXIES: list[dict] = []


def _get_headers() -> dict:
    """构建随机 UA + 固定语言头的请求头"""
    ua = random.choice(USER_AGENTS)
    return {
        "User-Agent": ua,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _get_proxy() -> Optional[dict]:
    """从 PROXIES 池轮流返回一项（Round-robin）"""
    if not PROXIES:
        return None
    proxy = random.choice(PROXIES)
    log.debug(f"使用代理: {proxy.get('http', proxy.get('https', ''))}")
    return proxy


# ─────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────
@dataclass
class LinkedInProfile:
    name: str = ""
    headline: str = ""          # 职位/头衔
    company: str = ""            # 公司
    industry: str = ""           # 行业
    location: str = ""           # 地区
    profile_url: str = ""        # 个人主页链接
    about: str = ""             # 个人简介
    connections: str = ""        # 连接数（可见时）
    raw_html_preview: str = ""   # 原始 HTML 片段（调试用，仅取前200字符）


# ─────────────────────────────────────────────
# 请求层 — 含重试、超时、UA 轮换
# ─────────────────────────────────────────────
def fetch_page(url: str, timeout: int = 10, max_retries: int = 3) -> Optional[BeautifulSoup]:
    """
    获取任意 LinkedIn 页面 HTML
    - 随机 UA，防止频率指纹
    - 最多 max_retries 次重试（随机指数退避）
    - 支持代理轮换
    """
    for attempt in range(max_retries):
        headers = _get_headers()
        proxy = _get_proxy()
        try:
            resp = requests.get(
                url,
                headers=headers,
                proxies=proxy,
                timeout=timeout,
                allow_redirects=True,
            )
            if resp.status_code == 999:
                # 触发了反爬，等长一点再重试
                backoff = random.uniform(5, 15)
                log.warning(f"状态码 999（被拦截），等待 {backoff:.0f}s 后重试...")
                time.sleep(backoff)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0.5, 2.0)
                log.warning(f"[尝试 {attempt+1}/{max_retries}] 请求失败: {e}，{wait:.1f}s 后重试...")
                time.sleep(wait)
            else:
                log.error(f"[最终失败] {url} → {e}")
    return None


# ─────────────────────────────────────────────
# 个人主页解析
# ─────────────────────────────────────────────
def parse_profile(soup: BeautifulSoup, url: str) -> LinkedInProfile:
    """从 HTML 解析 LinkedIn 公开个人资料"""
    profile = LinkedInProfile(profile_url=url)

    # 姓名
    name_tag = soup.select_one("h1")
    if name_tag:
        profile.name = name_tag.get_text(strip=True)

    # 副标题 / headline（多个备选选择器）
    for sel in (
        "[class*='headline']",
        "[class*='pv-top-card-v2-ctas']",
        ".pv-top-card-v2-ctas",
    ):
        tag = soup.select_one(sel)
        if tag:
            profile.headline = tag.get_text(strip=True)
            break

    # 备用：og:description
    if not profile.headline:
        desc = soup.find("meta", property="og:description")
        if desc and desc.get("content"):
            # 去掉引号
            profile.headline = desc["content"].strip().strip('"')

    # 地区
    for sel in ("[class*='location']", "[class*='geo']"):
        tag = soup.select_one(sel)
        if tag:
            profile.location = tag.get_text(strip=True)
            break

    # 行业
    ind_tag = soup.select_one("[class*='industry']")
    if ind_tag:
        profile.industry = ind_tag.get_text(strip=True)

    # 公司 — 从 headline 提取 "Title at Company" / "Title · Company"
    if profile.headline and not profile.company:
        parts = re.split(r"\s+at\s+|\s+@\s+|·\s+", profile.headline)
        if len(parts) > 1:
            profile.company = parts[-1].strip().strip('"')

    # 个人简介 about
    about_tag = soup.select_one("[class*='about'], [class*='summary']")
    if about_tag:
        profile.about = about_tag.get_text(strip=True)
    else:
        desc = soup.find("meta", property="og:description")
        if desc and desc.get("content"):
            profile.about = desc["content"].strip()

    # 连接数（有些公开页可见）
    conn_tag = soup.select_one("[class*='connection']")
    if conn_tag:
        profile.connections = conn_tag.get_text(strip=True)

    # HTML 调试片段
    main_tag = soup.select_one("main, [class*='profile']")
    if main_tag:
        profile.raw_html_preview = main_tag.get_text()[:200].strip()

    return profile


# ─────────────────────────────────────────────
# 搜索结果页解析
# ─────────────────────────────────────────────
def parse_search_results(soup: BeautifulSoup) -> list[str]:
    """从 LinkedIn 搜索结果页提取个人主页链接列表"""
    links = []
    seen = set()
    for a in soup.select("a[href*='/in/']"):
        href = a.get("href", "")
        if "/in/" not in href:
            continue
        clean = re.split(r"\?", href)[0].rstrip("/")
        if clean and clean not in seen:
            seen.add(clean)
            links.append(clean)
    return links


# ─────────────────────────────────────────────
# LinkedIn 关键词搜索 — 通过 Google/ Bing 间接抓取
#    ⚠️ 注意：LinkedIn 搜索页通常需要登录才能抓取
#    此函数通过 Google 搜索 "site:linkedin.com/in <keyword>"
#    返回最多 limit 个结果作为"初筛"列表
# ─────────────────────────────────────────────
def search_by_keyword_google(keyword: str, limit: int = 10, delay: float = 3.0) -> list[str]:
    """
    通过 Google 搜索 site:linkedin.com/in <keyword>
    返回符合条件的个人主页 URL 列表

    ⚠️ 此为间接方法，Google 可能需要 Captcha，建议：
    - 使用 SerpAPI / Google Custom Search API
    - 或使用代理池降低拦截概率
    """
    query = f"site:linkedin.com/in {keyword}"
    encoded_q = requests.utils.quote(query)
    # Google 搜索结果页 URL
    url = f"https://www.google.com/search?q={encoded_q}&num={min(limit, 10)}"

    headers = _get_headers()
    headers["Accept-Language"] = "en-US,en;q=0.9"

    log.info(f"搜索关键词: {keyword}")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Google 搜索请求失败: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    seen = set()

    for a in soup.select("a[href]"):
        href = a["href"]
        if "/url?q=" in href:
            # 提取真实 URL
            match = re.search(r"/url\?q=([^&]+)", href)
            if match:
                raw = requests.utils.unquote(match.group(1))
                if "/in/" in raw and raw not in seen:
                    clean = re.split(r"\?", raw)[0].rstrip("/")
                    seen.add(clean)
                    links.append(clean)
                    if len(links) >= limit:
                        break

    log.info(f"Google 搜索找到 {len(links)} 个 LinkedIn 个人主页")
    time.sleep(delay)
    return links


# ─────────────────────────────────────────────
# 批量抓取
# ─────────────────────────────────────────────
def scrape_profiles(urls: list[str], delay: float = 2.0) -> list[LinkedInProfile]:
    """
    批量抓取多个个人主页
    - 每次请求间隔 delay 秒（+ 随机抖动 ±0.5s）
    - 实时打印进度
    """
    results = []
    for i, url in enumerate(urls, 1):
        # 清理 URL
        url = re.split(r"\?", url)[0].rstrip("/")
        print(f"[{i}/{len(urls)}] 正在抓取: {url}")
        soup = fetch_page(url)
        if soup:
            profile = parse_profile(soup, url)
            results.append(profile)
            print(
                f"  ✓ {profile.name} | {profile.headline[:40]} "
                f"| {profile.location}"
            )
        else:
            print(f"  ✗ 抓取失败，跳过")
        # 随机抖动延迟
        jitter = random.uniform(-0.5, 0.5)
        time.sleep(max(0.5, delay + jitter))
    return results


# ─────────────────────────────────────────────
# 保存
# ─────────────────────────────────────────────
def save_csv(profiles: list[LinkedInProfile], filename: str = "linkedin_profiles.csv"):
    if not profiles:
        log.info("无数据可保存")
        return
    keys = [
        "name", "headline", "company", "industry",
        "location", "connections", "profile_url", "about",
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([asdict(p) for p in profiles])
    log.info(f"✓ 已保存 {len(profiles)} 条数据 → {filename}")


def save_json(profiles: list[LinkedInProfile], filename: str = "linkedin_profiles.json"):
    if not profiles:
        log.info("无数据可保存")
        return
    with open(filename, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in profiles], f, ensure_ascii=False, indent=2)
    log.info(f"✓ 已保存 {len(profiles)} 条数据 → {filename}")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn 公开个人主页爬虫（含关键词搜索）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例:
  # 抓取单个个人主页
  python linkedin_scraper.py https://uk.linkedin.com/in/johndoe

  # 批量抓取多个 URL
  python linkedin_scraper.py url1 url2 url3 -o json

  # 从文件读取 URL 列表
  python linkedin_scraper.py -f urls.txt -o both

  # 关键词搜索（通过 Google）
  python linkedin_scraper.py -k "software engineer London UK" --search-limit 20

  # 配置代理: 编辑脚本顶部 PROXIES 变量
        """,
    )
    parser.add_argument("urls", nargs="*", help="LinkedIn 个人主页 URL（可多个）")
    parser.add_argument("-f", "--file", help="从文件读取 URL 列表（一行一个）")
    parser.add_argument("-k", "--keyword", help="关键词搜索（通过 Google site:linkedin.com/in）")
    parser.add_argument("--search-limit", type=int, default=10,
                        help="关键词搜索返回的最大结果数（默认 10）")
    parser.add_argument("-o", "--output", choices=["csv", "json", "both"], default="csv")
    parser.add_argument("-d", "--delay", type=float, default=2.0,
                        help="每次请求间隔秒数（默认 2s）")
    parser.add_argument("-v", "--verbose", action="store_true", help="打印详细日志")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 收集 URL
    urls = list(args.urls)
    if args.file:
        with open(args.file, "r") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    # 关键词搜索
    if args.keyword:
        keyword_urls = search_by_keyword_google(args.keyword, limit=args.search_limit, delay=args.delay)
        urls.extend(keyword_urls)

    if not urls:
        log.error("未提供任何 URL，请使用 --file、--keyword 或直接传入 URL")
        return

    # 去重
    urls = list(dict.fromkeys(urls))

    profiles = scrape_profiles(urls, delay=args.delay)

    if args.output in ("csv", "both"):
        save_csv(profiles)
    if args.output in ("json", "both"):
        save_json(profiles)


if __name__ == "__main__":
    main()
