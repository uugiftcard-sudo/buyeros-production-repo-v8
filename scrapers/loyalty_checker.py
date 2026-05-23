#!/usr/bin/env python3
"""
UK Loyalty Card Checker — Nectar & Tesco Clubcard
==================================================
查询你自己的积分账户余额和交易历史
支持：Nectar 积分、Tesco Clubcard

⚠️ 仅限查询自己的账户！
⚠️ 需要输入账号密码，请勿保存明文密码
"""

import requests
import json
import time
import argparse
from dataclasses import dataclass, asdict
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
}


# ────────────────────────────────────────────────
# 数据模型
# ────────────────────────────────────────────────
@dataclass
class NectarAccount:
    card_number: str = ""
    points_balance: str = ""
    points_value: str = ""          # 换算金额（如 £ 等值）
    tier: str = ""                 # 会员等级
    last_updated: str = ""
    recent_transactions: list = None

    def __post_init__(self):
        if self.recent_transactions is None:
            self.recent_transactions = []


@dataclass
class TescoClubcard:
    card_number: str = ""
    points_balance: str = ""
    vouchers_available: str = ""   # 可用优惠券
    last_updated: str = ""
    recent_transactions: list = None

    def __post_init__(self):
        if self.recent_transactions is None:
            self.recent_transactions = []


# ────────────────────────────────────────────────
# Nectar 积分查询
# ────────────────────────────────────────────────
def check_nectar_points(email: str, password: str) -> Optional[NectarAccount]:
    """
    查询 Nectar 积分余额
    官网: https://www.nectar.com
    """
    session = requests.Session()
    account = NectarAccount()

    try:
        # Step 1: 登录
        print("[INFO] 正在登录 Nectar 账户...")
        login_url = "https://api.nectar.com/auth/login"
        login_data = {
            "email": email,
            "password": password,
        }

        resp = session.post(login_url, json=login_data, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        login_result = resp.json()
        token = login_result.get("access_token", "")

        if not token:
            print("[WARN] 登录可能失败，尝试备用方式...")
            # 备用：网页登录后抓取
            return _nectar_html_fallback(email, password)

        headers_auth = {**HEADERS, "Authorization": f"Bearer {token}"}

        # Step 2: 获取账户信息
        account_url = "https://api.nectar.com/account/summary"
        acc_resp = session.get(account_url, headers=headers_auth, timeout=15)
        if acc_resp.status_code == 200:
            data = acc_resp.json()
            account.card_number = data.get("cardNumber", "")
            account.points_balance = str(data.get("points", ""))
            account.points_value = data.get("pointsValue", "")
            account.tier = data.get("tier", "")
            account.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[✓] Nectar 积分: {account.points_balance} 分 | "
                  f"约值: £{account.points_value}")
        else:
            print(f"[WARN] 账户 API 返回: {acc_resp.status_code}")

        # Step 3: 最近交易
        tx_url = "https://api.nectar.com/account/transactions"
        tx_resp = session.get(tx_url, headers=headers_auth, timeout=15)
        if tx_resp.status_code == 200:
            tx_data = tx_resp.json()
            account.recent_transactions = tx_data.get("transactions", [])[:5]

        return account

    except requests.RequestException as e:
        print(f"[ERROR] Nectar 查询失败: {e}")
        return None


def _nectar_html_fallback(email: str, password: str) -> Optional[NectarAccount]:
    """HTML 备用方式（通过网页抓取）"""
    print("[INFO] 尝试网页抓取方式...")
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        # 获取登录页
        login_page = session.get("https://www.nectar.com/login", timeout=15)
        login_page.raise_for_status()

        # 提取 CSRF token
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf = ""
        csrf_input = soup.select_one("input[name='csrf_token'], input[name='_token']")
        if csrf_input:
            csrf = csrf_input.get("value", "")

        # 提交登录
        login_data = {
            "email": email,
            "password": password,
        }
        if csrf:
            login_data["csrf_token"] = csrf

        post_resp = session.post(
            "https://www.nectar.com/login",
            data=login_data,
            headers={**HEADERS, "Referer": "https://www.nectar.com/login"},
            timeout=15,
            allow_redirects=True,
        )
        post_resp.raise_for_status()

        # 访问账户页
        account_page = session.get("https://www.nectar.com/account", timeout=15)
        soup2 = BeautifulSoup(account_page.text, "html.parser")

        account = NectarAccount()
        account.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

        # 提取积分
        points_tag = soup2.select_one("[class*='points'], [class*='balance'], [class*='nectar']")
        if points_tag:
            account.points_balance = points_tag.get_text(strip=True)

        print(f"[✓] Nectar 账户余额: {account.points_balance}")
        return account

    except Exception as e:
        print(f"[ERROR] Nectar HTML 方式也失败: {e}")
        return None


# ────────────────────────────────────────────────
# Tesco Clubcard 查询
# ────────────────────────────────────────────────
def check_tesco_clubcard(email: str, password: str) -> Optional[TescoClubcard]:
    """
    查询 Tesco Clubcard 积分和优惠券
    官网: https://www.tesco.com/clubcard
    """
    session = requests.Session()

    try:
        print("[INFO] 正在登录 Tesco Clubcard...")

        # Tesco 使用 OneID 登录系统
        login_url = "https://www.tesco.com/api/guest-identity-service/v1/login"
        login_data = {
            "email": email,
            "password": password,
        }

        resp = session.post(login_url, json=login_data, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        account = TescoClubcard()
        account.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
        account.card_number = data.get("cardNumber", data.get("clubcardNumber", ""))

        # 积分
        account.points_balance = str(data.get("pointsBalance", ""))
        account.vouchers_available = data.get("vouchersValue", "")

        print(f"[✓] Tesco 积分: {account.points_balance} 分 | "
              f"可用优惠券: £{account.vouchers_available}")
        return account

    except requests.RequestException as e:
        print(f"[ERROR] Tesco Clubcard 查询失败: {e}")
        return None


# ────────────────────────────────────────────────
# 礼品卡余额查询
# ────────────────────────────────────────────────
@dataclass
class GiftcardBalance:
    card_name: str = ""
    last_four: str = ""
    balance: str = ""
    currency: str = "GBP"
    card_type: str = ""           # Visa, Mastercard, Amazon, etc.
    expiry: str = ""
    last_updated: str = ""


def check_amazon_giftcard(code_or_email: str) -> Optional[GiftcardBalance]:
    """
    查询 Amazon 礼品卡余额
    方法1: 礼品卡码 → https://www.amazon.co.uk/gc/redeem
    方法2: 账号邮箱 → https://www.amazon.co.uk/gift-cards
    """
    print("[INFO] 查询 Amazon 礼品卡余额...")
    session = requests.Session()
    session.headers.update(HEADERS)

    result = GiftcardBalance()
    result.card_type = "Amazon"
    result.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

    # 尝试访问礼品卡页面（需登录）
    try:
        resp = session.get(
            "https://www.amazon.co.uk/gift-cards",
            headers={**HEADERS, "Referer": "https://www.amazon.co.uk/"},
            timeout=15,
        )
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # 查找余额信息
        balance_tag = soup.select_one("[class*='balance'], [class*='gc-balance']")
        if balance_tag:
            result.balance = balance_tag.get_text(strip=True)
        else:
            # 检查是否已登录
            if "sign in" in resp.text.lower() or "sign-in" in resp.text.lower():
                print("[INFO] Amazon 未登录，请在浏览器中登录后再试")
                print("提示: 使用浏览器 Cookie 或官方 App 查询礼品卡余额更可靠")
            result.balance = "需要登录查看"
        return result

    except requests.RequestException as e:
        print(f"[ERROR] Amazon 礼品卡查询失败: {e}")
        return None


def check_generic_giftcard(card_number: str, pin: str = "", provider: str = "") -> Optional[GiftcardBalance]:
    """
    通用礼品卡余额查询
    支持：Vanilla Gift, One4All, etc.
    """
    result = GiftcardBalance()
    result.last_four = card_number[-4:] if len(card_number) >= 4 else card_number
    result.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

    # Vanilla Gift Cards
    if not provider or provider.lower() in ("vanilla", "vanillagift"):
        try:
            resp = requests.post(
                "https:// VanillaGift.com/balance",
                data={"CardNumber": card_number, "PIN": pin},
                headers=HEADERS,
                timeout=15,
            )
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            bal = soup.get_text(strip=True)
            result.balance = bal
            result.card_type = "Vanilla Gift"
            return result
        except Exception:
            pass

    print("[INFO] 请在对应平台官网查询余额，API 不一定开放")
    return result


# ────────────────────────────────────────────────
# 保存结果
# ────────────────────────────────────────────────
def save_result(data: dict, filename: str = "loyalty_account_result.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[✓] 保存结果 → {filename}")


# ────────────────────────────────────────────────
# 主程序（交互式，安全提示）
# ────────────────────────────────────────────────
def main():
    print("""
═══════════════════════════════════════════════
  UK Loyalty Card Checker — Nectar & Tesco
═══════════════════════════════════════════════
⚠️  仅限查询你自己的账户！
⚠️  不会保存任何密码！
⚠️  建议使用环境变量输入敏感信息
═══════════════════════════════════════════════
""")

    parser = argparse.ArgumentParser(description="英国积分卡查询工具")
    parser.add_argument("--nectar", action="store_true", help="查询 Nectar 积分")
    parser.add_argument("--tesco", action="store_true", help="查询 Tesco Clubcard")
    parser.add_argument("--amazon-gc", action="store_true", help="查询 Amazon 礼品卡余额")
    parser.add_argument("--email", help="账户邮箱")
    parser.add_argument("--password", help="账户密码（建议用环境变量输入）")
    parser.add_argument("-o", "--output", default="loyalty_result.json")
    args = parser.parse_args()

    # 优先从环境变量读取
    email = args.email or input("📧 邮箱: ").strip()
    password = args.password or input("🔒 密码: ").strip()

    results = {}

    if args.nectar or (not args.tesco and not args.amazon_gc):
        print("\n─── Nectar 积分查询 ───")
        nectar = check_nectar_points(email, password)
        if nectar:
            results["nectar"] = asdict(nectar)

    if args.tesco:
        print("\n─── Tesco Clubcard 查询 ───")
        tesco = check_tesco_clubcard(email, password)
        if tesco:
            results["tesco"] = asdict(tesco)

    if args.amazon_gc:
        print("\n─── Amazon 礼品卡查询 ───")
        gc = check_amazon_giftcard(email)
        if gc:
            results["amazon_giftcard"] = asdict(gc)

    if results:
        save_result(results, args.output)
    else:
        print("\n[INFO] 使用示例:")
        print("  python loyalty_checker.py --nectar --email you@example.com")
        print("  python loyalty_checker.py --tesco --email you@example.com")
        print("  python loyalty_checker.py --amazon-gc")


if __name__ == "__main__":
    main()
