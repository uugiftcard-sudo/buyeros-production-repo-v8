"""
B2B Contact Finder — Apollo.io, Hunter.io, Companies House UK.

Finds professional contacts by company domain, keyword, or UK company name.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.config import get_settings
from src.models.b2b import B2BContact, UKCompany
from src.utils.html import make_soup

_LOG = logging.getLogger(__name__)

_APOLLO_BASE = "https://api.apollo.io/v1"
_HUNTER_BASE = "https://api.hunter.io/v2"
_CH_BASE = "https://api.companyinformation.service.gov.uk"


class B2BScraper:
    """
    B2B contact finder using Apollo.io, Hunter.io, and Companies House UK.

    No authentication needed for Companies House.
    Apollo/Hunter require API keys (set APOLLO_API_KEY / HUNTER_API_KEY env vars).
    """

    name = "b2b"

    def __init__(
        self,
        apollo_key: str | None = None,
        hunter_key: str | None = None,
        delay: float = 1.0,
    ) -> None:
        settings = get_settings()
        self.apollo_key = apollo_key or settings.apollo_api_key
        self.hunter_key = hunter_key or settings.hunter_api_key
        self.delay = delay

    # ── Apollo.io ──────────────────────────────────────────────

    def search_apollo_by_domain(self, domain: str, limit: int = 10) -> list[B2BContact]:
        """Search employees by company domain."""
        if not self.apollo_key or self.apollo_key == "your_apollo_key_here":
            _LOG.warning("Apollo API key not configured — skipping")
            return []

        contacts: list[B2BContact] = []
        url = f"{_APOLLO_BASE}/people/search"
        headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
        payload = {
            "api_key": self.apollo_key,
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

            _LOG.info(f"[Apollo] Found {len(contacts)} contacts for {domain}")

        except requests.RequestException as e:
            _LOG.error(f"[Apollo] Request failed: {e}")

        return contacts

    def search_apollo_by_keyword(
        self,
        keyword: str,
        title: str = "",
        country: str = "",
        limit: int = 10,
    ) -> list[B2BContact]:
        """Keyword-based person search via Apollo."""
        if not self.apollo_key or self.apollo_key == "your_apollo_key_here":
            _LOG.warning("Apollo API key not configured — skipping")
            return []

        contacts: list[B2BContact] = []
        url = f"{_APOLLO_BASE}/people/search"
        payload: dict[str, Any] = {
            "api_key": self.apollo_key,
            "q_keywords": keyword,
            "page_size": min(limit, 25),
        }
        if title:
            payload["person_titles"] = [title]
        if country:
            payload["countries"] = [country]

        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
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

            _LOG.info(f"[Apollo] Keyword search found {len(contacts)} contacts for '{keyword}'")

        except requests.RequestException as e:
            _LOG.error(f"[Apollo] Keyword search failed: {e}")

        return contacts

    # ── Hunter.io ─────────────────────────────────────────────

    def search_hunter_by_domain(self, domain: str, limit: int = 10) -> list[B2BContact]:
        """Find public email patterns for a domain."""
        if not self.hunter_key or self.hunter_key == "your_hunter_key_here":
            _LOG.warning("Hunter API key not configured — skipping")
            return []

        contacts: list[B2BContact] = []
        url = f"{_HUNTER_BASE}/domain-search"
        params = {"api_key": self.hunter_key, "domain": domain, "limit": min(limit, 10)}

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

            _LOG.info(f"[Hunter] Found {len(contacts)} emails for {domain}")

        except requests.RequestException as e:
            _LOG.error(f"[Hunter] Request failed: {e}")

        return contacts

    def search_hunter_by_email_finder(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> str | None:
        """Find a specific email from name + domain."""
        if not self.hunter_key or self.hunter_key == "your_hunter_key_here":
            return None

        url = f"{_HUNTER_BASE}/email-finder"
        params = {
            "api_key": self.hunter_key,
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("email")
        except requests.RequestException:
            return None

    # ── Companies House ─────────────────────────────────────────

    def search_companies_house(
        self,
        company_name: str,
        items_per_page: int = 10,
    ) -> list[UKCompany]:
        """Search UK companies (official free API, no key required)."""
        url = f"{_CH_BASE}/search/companies"
        params = {"q": company_name, "items_per_page": items_per_page}
        companies: list[UKCompany] = []

        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

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
                c.detail_url = (
                    f"https://find-and-update.company-information.service.gov.uk/company/{c.number}"
                )
                companies.append(c)

            _LOG.info(f"[Companies House] Found {len(companies)} companies for '{company_name}'")

        except requests.RequestException as e:
            _LOG.error(f"[Companies House] Search failed: {e}")

        return companies

    def get_company_details(self, company_number: str) -> dict[str, Any]:
        """Fetch detailed company info from Companies House."""
        url = f"{_CH_BASE}/company/{company_number}"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            _LOG.info(f"[Companies House] Fetched details for {company_number}")
            return {
                "company_number": data.get("company_number", ""),
                "title": data.get("company_name", ""),
                "type": data.get("type", ""),
                "status": data.get("company_status", ""),
                "incorporation_date": data.get("date_of_creation", ""),
                "address": data.get("registered_office_address", {}),
                "sic_codes": data.get("sic_codes", []),
                "accounts": data.get("accounts", {}),
            }
        except requests.RequestException as e:
            _LOG.error(f"[Companies House] Details fetch failed: {e}")
            return {}

    def get_company_officers(self, company_number: str) -> list[dict[str, Any]]:
        """Fetch company officer/director list."""
        url = f"{_CH_BASE}/company/{company_number}/officers"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json().get("items", []) or []
        except requests.RequestException as e:
            _LOG.error(f"[Companies House] Officers fetch failed: {e}")
            return []

    def search_all(
        self,
        domain: str | None = None,
        keyword: str | None = None,
        company: str | None = None,
        platform: str = "all",
    ) -> tuple[list[B2BContact], list[UKCompany]]:
        """
        Unified search across all available sources.

        Returns (contacts, companies).
        """
        contacts: list[B2BContact] = []
        companies: list[UKCompany] = []

        if company:
            companies = self.search_companies_house(company)

        elif domain:
            if platform in ("apollo", "all"):
                contacts += self.search_apollo_by_domain(domain)
                time.sleep(self.delay)
            if platform in ("hunter", "all"):
                contacts += self.search_hunter_by_domain(domain)

        elif keyword:
            if platform in ("apollo", "all"):
                contacts = self.search_apollo_by_keyword(keyword)

        return contacts, companies
