"""
UK Loyalty Card Checker — Nectar, Tesco Clubcard, Amazon Gift Card.

⚠️ Only query YOUR OWN accounts. Credentials are never stored.
"""

from __future__ import annotations

import logging
import time

import requests

from src.models.loyalty import GiftcardBalance, NectarAccount, TescoClubcard
from src.scrapers.base import BaseScraper
from src.utils.html import make_soup

_LOG = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
}


class LoyaltyScraper(BaseScraper[NectarAccount]):
    """
    UK loyalty card and gift card balance checker.

    Example:
        scraper = LoyaltyScraper()
        nectar = scraper.check_nectar(email, password)
        tesco = scraper.check_tesco(email, password)
    """

    name = "loyalty"

    def __init__(self, delay: float = 5.0) -> None:
        # Slower delay for auth-based scrapers
        super().__init__(delay=delay, max_retries=1)
        self.session = requests.Session()
        self.session.headers.update(_HEADERS)

    def scrape_item(self, url: str) -> NectarAccount | None:
        raise NotImplementedError("Use specific check_* methods instead")

    # ── Nectar ──────────────────────────────────────────────────

    def check_nectar(self, email: str, password: str) -> NectarAccount | None:
        """
        Query Nectar account balance.

        Tries the API first, falls back to HTML scraping.
        """
        account = NectarAccount()

        # Try API
        try:
            login_resp = self.session.post(
                "https://api.nectar.com/auth/login",
                json={"email": email, "password": password},
                timeout=15,
            )
            login_resp.raise_for_status()
            token = login_resp.json().get("access_token", "")

            if not token:
                return self._nectar_html(email, password)

            headers_auth = {**_HEADERS, "Authorization": f"Bearer {token}"}

            acc_resp = self.session.get(
                "https://api.nectar.com/account/summary",
                headers=headers_auth,
                timeout=15,
            )
            if acc_resp.status_code == 200:
                data = acc_resp.json()
                account.card_number = data.get("cardNumber", "")
                account.points_balance = str(data.get("points", ""))
                account.points_value = data.get("pointsValue", "")
                account.tier = data.get("tier", "")
                account.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

            tx_resp = self.session.get(
                "https://api.nectar.com/account/transactions",
                headers=headers_auth,
                timeout=15,
            )
            if tx_resp.status_code == 200:
                account.recent_transactions = tx_resp.json().get("transactions", [])[:5]

            _LOG.info(f"[Nectar] Points: {account.points_balance} | Value: £{account.points_value}")
            return account

        except requests.RequestException as e:
            _LOG.warning(f"[Nectar] API failed: {e}, trying HTML fallback")
            return self._nectar_html(email, password)

    def _nectar_html(self, email: str, password: str) -> NectarAccount | None:
        """HTML fallback for Nectar (requires login)."""
        account = NectarAccount()
        account.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            # Get CSRF token
            login_page = self.session.get("https://www.nectar.com/login", timeout=15)
            login_page.raise_for_status()
            soup = make_soup(login_page.text)
            csrf_input = soup.select_one("input[name='csrf_token'], input[name='_token']")
            csrf = csrf_input.get("value", "") if csrf_input else ""

            login_data: dict[str, str] = {"email": email, "password": password}
            if csrf:
                login_data["csrf_token"] = csrf

            self.session.post(
                "https://www.nectar.com/login",
                data=login_data,
                headers={**_HEADERS, "Referer": "https://www.nectar.com/login"},
                timeout=15,
                allow_redirects=True,
            )

            account_page = self.session.get("https://www.nectar.com/account", timeout=15)
            soup2 = make_soup(account_page.text)

            points_tag = soup2.select_one("[class*='points'], [class*='balance']")
            if points_tag:
                account.points_balance = points_tag.get_text(strip=True)

            _LOG.info(f"[Nectar HTML] Balance: {account.points_balance}")
            return account

        except requests.RequestException as e:
            _LOG.error(f"[Nectar HTML] Failed: {e}")
            return None

    # ── Tesco Clubcard ─────────────────────────────────────────

    def check_tesco(self, email: str, password: str) -> TescoClubcard | None:
        """Query Tesco Clubcard balance."""
        account = TescoClubcard()
        account.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            resp = self.session.post(
                "https://www.tesco.com/api/guest-identity-service/v1/login",
                json={"email": email, "password": password},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            account.card_number = data.get("cardNumber", data.get("clubcardNumber", ""))
            account.points_balance = str(data.get("pointsBalance", ""))
            account.vouchers_available = data.get("vouchersValue", "")

            _LOG.info(
                f"[Tesco] Points: {account.points_balance} | "
                f"Vouchers: £{account.vouchers_available}"
            )
            return account

        except requests.RequestException as e:
            _LOG.error(f"[Tesco] Request failed: {e}")
            return None

    # ── Amazon Gift Card ────────────────────────────────────────

    def check_amazon_giftcard(self, code_or_email: str) -> GiftcardBalance | None:
        """Query Amazon gift card balance (requires login)."""
        result = GiftcardBalance()
        result.card_type = "Amazon"
        result.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            resp = self.session.get(
                "https://www.amazon.co.uk/gift-cards",
                headers={**_HEADERS, "Referer": "https://www.amazon.co.uk/"},
                timeout=15,
            )
            resp.raise_for_status()
            soup = make_soup(resp.text)

            balance_tag = soup.select_one("[class*='balance'], [class*='gc-balance']")
            if balance_tag:
                result.balance = balance_tag.get_text(strip=True)
            else:
                if "sign in" in resp.text.lower():
                    result.balance = "Requires login"
                else:
                    result.balance = "Not found"

            _LOG.info(f"[Amazon GC] Balance: {result.balance}")
            return result

        except requests.RequestException as e:
            _LOG.error(f"[Amazon GC] Request failed: {e}")
            return None

    # ── Generic gift card ───────────────────────────────────────

    def check_generic_giftcard(
        self,
        card_number: str,
        pin: str = "",
        provider: str = "",
    ) -> GiftcardBalance | None:
        """Generic gift card balance lookup."""
        result = GiftcardBalance()
        result.last_four = card_number[-4:] if len(card_number) >= 4 else card_number
        result.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
        return result
