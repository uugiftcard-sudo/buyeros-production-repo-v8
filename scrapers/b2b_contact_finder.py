#!/usr/bin/env python3
"""
B2B Contact Finder — Apollo.io + Hunter.io + Companies House
===========================================================
通过公司域名查找 B2B 联系人（姓名、职位、公司、行业）
- Apollo.io API（每月免费 50 次查找）
- Hunter.io API（每月免费 25 次查找）
- Companies House 英国公司查询（官方免费，无需 API Key）

⚠️ 合规提醒：
- 请遵守各平台使用条款
- 禁止未经同意的批量营销
- 免费层额度有限，请合理使用
"""

import os
import requests
import csv
import json
import time
import argparse
from dataclasses import dataclass, asdict, field
from typing import Optional

# ────────────────────────────────────────────────
# 配置区 — 从环境变量或直接填入
# ────────────────────────────────────────────────
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "YOUR_APOLLO_API_KEY")
HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY", "YOUR_HUNTER_API_KEY")

# ────────────────────────────────────────────────
# 数据模型
# ────────────────────────────────────────────────
@dataclass
class B2BContact:
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    title: str = ""
    company: str = ""
    industry: str = ""
    seniority_level: str = ""
    department: str = ""
    linkedin_url: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    country: str = ""
    source: str = ""
    raw_data: dict = field(default_factory=dict)


@dataclass
class UKCompany:
    """Companies House 返回的英国公司信息"""
    number: str = ""
    title: str = ""
    company_type: str = ""
    status: str = ""
    jurisdiction: str = ""
    address_line_1: str = ""
    locality: str = ""
    postal_code: str = ""
    country: str = ""
    incorporation_date: str = ""
    nature_of_business: str = ""
    accounts_next_due: str = ""
    sic_codes: str = ""
    detail_url: str = ""


# ────────────────────────────────────────────────
# Apollo.io API
# ────────────────────────────────────────────────
def search_apollo_by_domain(domain: str, limit: int = 10) -> list[B2BContact]:
    """通过公司域名搜索员工"""
    contacts = []
    if APOLLO_API_KEY in ("YOUR_APOLLO_API_KEY", ""):
        print("[WARN] Apollo API Key 未配置，跳过 | set APOLLO_API_KEY env var")
        return contacts

    url = "https://api.apollo.io/v1/people/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    payload = {
        "api_key": APOLLO_API_KEY,
        "q_organization_domains": domain,
        "page_size": min(limit, 25),
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for person in data.get("people", []) or []:
            c = B2BContact(source="apollo")
            c.full_name = person.get("name", "")
            c.first_name = person.get("first_name", "")
            c.last_name = person.get("last_name", "")
            c.title = person.get("title", "")
            c.company = person.get("organization_name", "")
            c.industry = person.get("industry", "")
            c.seniority_level = person.get("seniority_level", "")
            dept_list = person.get("departments") or []
            c.department = dept_list[0] if dept_list else ""
            c.linkedin_url = person.get("linkedin_url", "")
            c.city = person.get("city", "")
            c.country = person.get("country", "")
            c.email = person.get("email", "")
            c.phone = person.get("phone_number", "")
            c.raw_data = person
            contacts.append(c)

        print(f"[Apollo] 找到 {len(contacts)} 条联系人 ← {domain}")

    except requests.RequestException as e:
        print(f"[ERROR] Apollo API 请求失败: {e}")

    return contacts


def search_apollo_by_keyword(
    keyword: str,
    title: str = "",
    country: str = "",
    limit: int = 10,
) -> list[B2BContact]:
    """
    通过关键词（职位 / 公司名 / 地区）搜索人员
    免费账号同样每月 50 次额度
    """
    contacts = []
    if APOLLO_API_KEY in ("YOUR_APOLLO_API_KEY", ""):
        print("[WARN] Apollo API Key 未配置，跳过 | set APOLLO_API_KEY env var")
        return contacts

    url = "https://api.apollo.io/v1/people/search"
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    payload = {
        "api_key": APOLLO_API_KEY,
        "q_keywords": keyword,
        "page_size": min(limit, 25),
    }
    if title:
        payload["person_titles"] = [title]
    if country:
        payload["countries"] = [country]

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for person in data.get("people", []) or []:
            c = B2BContact(source="apollo")
            c.full_name = person.get("name", "")
            c.first_name = person.get("first_name", "")
            c.last_name = person.get("last_name", "")
            c.title = person.get("title", "")
            c.company = person.get("organization_name", "")
            c.industry = person.get("industry", "")
            c.seniority_level = person.get("seniority_level", "")
            c.department = (person.get("departments") or [""])[0]
            c.linkedin_url = person.get("linkedin_url", "")
            c.city = person.get("city", "")
            c.country = person.get("country", "")
            c.email = person.get("email", "")
            c.phone = person.get("phone_number", "")
            c.raw_data = person
            contacts.append(c)

        print(f"[Apollo] 关键词搜索找到 {len(contacts)} 条 ← {keyword}")

    except requests.RequestException as e:
        print(f"[ERROR] Apollo 关键词搜索失败: {e}")

    return contacts


# ────────────────────────────────────────────────
# Hunter.io API
# ────────────────────────────────────────────────
def search_hunter_by_domain(domain: str, limit: int = 10) -> list[B2BContact]:
    """通过公司域名查找公开邮箱（免费 25 次/月）"""
    contacts = []
    if HUNTER_API_KEY in ("YOUR_HUNTER_API_KEY", ""):
        print("[WARN] Hunter API Key 未配置，跳过 | set HUNTER_API_KEY env var")
        return contacts

    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "api_key": HUNTER_API_KEY,
        "domain": domain,
        "limit": min(limit, 10),
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        org = data.get("data", {})
        company_name = org.get("organization", "")

        for email_entry in org.get("emails", []) or []:
            c = B2BContact(source="hunter")
            email_val = email_entry.get("value", "")
            local = email_val.split("@")[0] if "@" in email_val else ""
            c.email = email_val
            c.first_name = email_entry.get("first_name") or (
                local.split(".")[0] if "." in local else local
            )
            c.last_name = email_entry.get("last_name", "")
            c.full_name = f"{c.first_name} {c.last_name}".strip()
            c.title = email_entry.get("position", "")
            c.company = company_name
            lnk = email_entry.get("linkedin")
            c.linkedin_url = lnk.get("uri") if isinstance(lnk, dict) else ""
            c.raw_data = email_entry
            contacts.append(c)

        print(f"[Hunter] 找到 {len(contacts)} 条邮箱 ← {domain}")

    except requests.RequestException as e:
        print(f"[ERROR] Hunter API 请求失败: {e}")

    return contacts


def search_hunter_by_email_finder(
    first_name: str,
    last_name: str,
    domain: str,
) -> Optional[str]:
    """
    通过姓名 + 域名查找具体邮箱
    免费账号每请求消耗 1 次额度
    """
    if HUNTER_API_KEY in ("YOUR_HUNTER_API_KEY", ""):
        return None

    url = "https://api.hunter.io/v2/email-finder"
    params = {
        "api_key": HUNTER_API_KEY,
        "first_name": first_name,
        "last_name": last_name,
        "domain": domain,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        email_data = data.get("data", {})
        return email_data.get("email")
    except requests.RequestException:
        return None


# ────────────────────────────────────────────────
# Companies House 英国公司查询（官方免费 API）
# ────────────────────────────────────────────────
CH_BASE_URL = "https://api.companyinformation.service.gov.uk"


def search_companies_house(company_name: str, items_per_page: int = 10) -> list[UKCompany]:
    """
    搜索英国公司（官方免费 API，无需 Key）
    频率限制：每分钟 10 次请求
    """
    url = f"{CH_BASE_URL}/search/companies"
    params = {"q": company_name, "items_per_page": items_per_page}

    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        companies = []
        for item in data.get("items", []) or []:
            c = UKCompany()
            addr = item.get("registered_office_address") or {}
            c.number = item.get("company_number", "")
            c.title = item.get("title", "")
            c.company_type = item.get("company_type", "")
            c.status = item.get("company_status", "")
            c.jurisdiction = item.get("jurisdiction", "")
            c.address_line_1 = addr.get("address_line_1", "")
            c.locality = addr.get("locality", "")
            c.postal_code = addr.get("postal_code", "")
            c.country = addr.get("country", "")
            c.incorporation_date = item.get("date_of_creation", "")
            c.nature_of_business = item.get("description", "")
            c.detail_url = f"https://find-and-update.company-information.service.gov.uk/company/{c.number}"
            companies.append(c)

        print(f"[Companies House] 找到 {len(companies)} 家公司 ← {company_name}")
        return companies

    except requests.RequestException as e:
        print(f"[ERROR] Companies House 搜索失败: {e}")
        return []


def get_company_details(company_number: str) -> dict:
    """获取英国公司详细信息（注册地址、董事、股东等）"""
    url = f"{CH_BASE_URL}/company/{company_number}"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        result = {
            "company_number": data.get("company_number", ""),
            "title": data.get("company_name", ""),
            "type": data.get("type", ""),
            "status": data.get("company_status", ""),
            "jurisdiction": data.get("jurisdiction", ""),
            "incorporation_date": data.get("date_of_creation", ""),
            "dissolution_date": data.get("dissolution_date", ""),
            "address": data.get("registered_office_address", {}),
            "nature_of_business": data.get("sic_codes", []),
            "accounts": {
                "next_due": data.get("accounts", {}).get("next_due", ""),
                "overdue": data.get("accounts", {}).get("overdue", ""),
            },
            "returns": data.get("returns", {}),
            "persons": data.get("persons", {}),
            "links": data.get("links", {}),
        }
        print(f"[Companies House] 已获取公司详情 ← {company_number}")
        return result

    except requests.RequestException as e:
        print(f"[ERROR] Companies House 详情获取失败: {e}")
        return {}


def get_company_officers(company_number: str) -> list[dict]:
    """获取公司董事列表"""
    url = f"{CH_BASE_URL}/company/{company_number}/officers"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        officers = data.get("items", []) or []
        print(f"[Companies House] 获取到 {len(officers)} 位董事 ← {company_number}")
        return officers
    except requests.RequestException as e:
        print(f"[ERROR] 董事列表获取失败: {e}")
        return []


# ────────────────────────────────────────────────
# 保存结果
# ────────────────────────────────────────────────
def save_contacts(contacts: list[B2BContact], filename: str = "b2b_contacts.csv"):
    if not contacts:
        print("[INFO] 无联系人数据可保存")
        return
    keys = [
        "full_name", "first_name", "last_name", "title", "company",
        "industry", "department", "seniority_level", "email", "phone",
        "city", "country", "linkedin_url", "source",
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([asdict(c) for c in contacts])
    print(f"[✓] 保存 {len(contacts)} 条 → {filename}")


def save_uk_companies(companies: list[UKCompany], filename: str = "uk_companies.csv"):
    if not companies:
        print("[INFO] 无公司数据可保存")
        return
    keys = [
        "number", "title", "company_type", "status", "jurisdiction",
        "address_line_1", "locality", "postal_code", "country",
        "incorporation_date", "nature_of_business", "detail_url",
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([asdict(c) for c in companies])
    print(f"[✓] 保存 {len(companies)} 家公司 → {filename}")


def save_json(data, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[✓] 保存 JSON → {filename}")


# ────────────────────────────────────────────────
# 主程序
# ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="B2B 联系人查找工具（Apollo + Hunter + Companies House）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
环境变量:
  export APOLLO_API_KEY=your_key
  export HUNTER_API_KEY=your_key

用法示例:
  # 通过域名查找 B2B 联系人
  python b2b_contact_finder.py --domain acme.com -o contacts.csv

  # Apollo 关键词搜索（职位 + 地区）
  python b2b_contact_finder.py --apollo-keyword "sales manager" --country GB

  # 搜索英国公司（无需 API Key）
  python b2b_contact_finder.py --company "Acme Ltd"

  # 获取英国公司详细信息
  python b2b_contact_finder.py --company-number "12345678" -o detail.json

  # 获取公司董事列表
  python b2b_contact_finder.py --company-number "12345678" --officers
        """,
    )

    # 域名/公司搜索
    parser.add_argument("--domain", help="公司域名，如 acme.com")
    parser.add_argument("--company", help="公司名称（Companies House 搜索）")
    parser.add_argument("--company-number", help="英国公司注册号（6-8位数字）")
    parser.add_argument("--platform", choices=["apollo", "hunter", "ch", "all"], default="all")

    # Apollo 关键词搜索
    parser.add_argument("--apollo-keyword", help="Apollo 关键词搜索（如 'sales manager'）")
    parser.add_argument("--apollo-title", default="", help="限定职位")
    parser.add_argument("--country", default="", help="限定国家（如 GB）")

    # 输出
    parser.add_argument("-o", "--output", default="b2b_contacts.csv")
    parser.add_argument("-l", "--limit", type=int, default=10)
    parser.add_argument("--officers", action="store_true", help="获取公司董事列表")
    parser.add_argument("-f", "--format", choices=["csv", "json", "both"], default="csv")

    args = parser.parse_args()

    # ── 公司详情 ───────────────────────────────
    if args.company_number and args.platform in ("ch", "all"):
        print(f"\n[英国公司] 注册号: {args.company_number}")
        if args.officers:
            officers = get_company_officers(args.company_number)
            save_json(officers, f"officers_{args.company_number}.json")
            for off in (officers or [])[:5]:
                print(
                    f"  👤 {off.get('name')} | "
                    f"角色: {off.get('officer_role')} | "
                    f"任命: {off.get('appointed_on', '')}"
                )
        else:
            details = get_company_details(args.company_number)
            save_json(details, args.output)

    # ── 英国公司搜索 ───────────────────────────
    elif args.company:
        results = search_companies_house(args.company, items_per_page=args.limit)
        if results:
            if args.format in ("csv", "both"):
                save_uk_companies(results, args.output)
            if args.format in ("json", "both"):
                save_json([asdict(c) for c in results], args.output.replace(".csv", ".json"))

            for c in results:
                addr = f"{c.address_line_1}, {c.locality}"
                print(
                    f"  📋 {c.title} | {c.company_type} | "
                    f"状态: {c.status} | {c.status} | 地址: {addr}"
                )

    # ── B2B 域名查找 ──────────────────────────
    elif args.domain:
        all_contacts = []
        if args.platform in ("apollo", "all"):
            all_contacts += search_apollo_by_domain(args.domain, limit=args.limit)
            time.sleep(1)
        if args.platform in ("hunter", "all"):
            all_contacts += search_hunter_by_domain(args.domain, limit=args.limit)

        if all_contacts:
            if args.format in ("csv", "both"):
                save_contacts(all_contacts, args.output)
            if args.format in ("json", "both"):
                save_json([asdict(c) for c in all_contacts], args.output.replace(".csv", ".json"))

            print("\n示例数据（前 3 条）:")
            for c in all_contacts[:3]:
                print(f"  {c.full_name} | {c.title} | {c.company} | {c.email}")
        else:
            print("[INFO] 无结果，请检查 API Key 配置或设置 APOLLO_API_KEY / HUNTER_API_KEY 环境变量")

    # ── Apollo 关键词搜索 ───────────────────────
    elif args.apollo_keyword:
        contacts = search_apollo_by_keyword(
            args.apollo_keyword,
            title=args.apollo_title,
            country=args.country,
            limit=args.limit,
        )
        if contacts:
            if args.format in ("csv", "both"):
                save_contacts(contacts, args.output)
            if args.format in ("json", "both"):
                save_json([asdict(c) for c in contacts], args.output.replace(".csv", ".json"))

    # ── 无参数 ─────────────────────────────────
    else:
        print("""
B2B Contact Finder — 用法说明
==========================================

环境变量（推荐）:
  export APOLLO_API_KEY=your_key
  export HUNTER_API_KEY=your_key

1. 通过域名查找 B2B 联系人（Apollo + Hunter）
  python b2b_contact_finder.py --domain acme.com -o contacts.csv

2. 仅用 Apollo
  python b2b_contact_finder.py --domain acme.com --platform apollo

3. 仅用 Hunter
  python b2b_contact_finder.py --domain acme.com --platform hunter

4. Apollo 关键词搜索（职位 + 国家）
  python b2b_contact_finder.py --apollo-keyword "sales manager" --country GB

5. 搜索英国公司（无需 API Key）
  python b2b_contact_finder.py --company "Acme Ltd"

6. 获取英国公司详细信息（需注册号）
  python b2b_contact_finder.py --company-number "12345678" -o detail.json

7. 获取公司董事列表
  python b2b_contact_finder.py --company-number "12345678" --officers

==========================================
免费额度（请勿滥用）:
  Apollo.io  : 50 次/月
  Hunter.io  : 25 次/月
  Companies House: ~600 次/小时（无 Key）
        """)


if __name__ == "__main__":
    main()
