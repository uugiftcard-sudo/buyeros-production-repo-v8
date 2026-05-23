#!/usr/bin/env python3
"""
scrapers — Unified Click CLI

Entry point: `scrapers` (installed via pyproject.toml console_scripts).

Usage:
    scrapers linkedin <url> [url2 ...]
    scrapers linkedin -f urls.txt
    scrapers linkedin -k "software engineer London"
    scrapers b2b --domain acme.com
    scrapers amazon --keyword "laptop" --pages 2
    scrapers trip --type flight --from LHR --to NRT --date 2025-06-15
    scrapers supermarket -c -k "whole milk"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table

from src.logging_config import setup_logging

if TYPE_CHECKING:
    pass

console = Console(stderr=True)

# ─── Storage helper ────────────────────────────────────────────────


def _save_and_report(items: list, output: str, format: str, name: str) -> None:
    """Save items and print a summary table."""
    if not items:
        console.print(f"[yellow]No results from {name}.[/yellow]")
        return

    from src.storage.writer import save_any

    path = save_any(items, output, format)
    console.print(f"[green]Saved {len(items)} results → {path}[/green]")

    # Pretty table of first 5 rows
    if hasattr(items[0], "model_fields"):
        _print_table(items[:5], name)


def _print_table(items: list, title: str) -> None:
    """Print a Rich table for the first few items."""
    if not items:
        return
    model = items[0]
    fields = list(model.model_fields.keys())[:6]  # First 6 columns
    table = Table(title=title, style="bold cyan")
    for f in fields:
        table.add_column(f.replace("_", " ").title(), overflow="fold")
    for item in items:
        row = [str(getattr(item, f, "") or "") for f in fields]
        table.add_row(*row)
    console.print(table)


# ─── Global options ────────────────────────────────────────────────


class GlobalOptions:
    def __init__(self):
        self.output: str = ""
        self.format: str = "csv"
        self.verbose: bool = False
        self.dry_run: bool = False


pass_opts = click.make_pass_decorator(GlobalOptions, ensure=True)


@click.group(cls=click.Group)
@click.option("--output", "-o", default="", help="Output file path")
@click.option(
    "--format",
    "-f",
    "output_format",
    default="csv",
    type=click.Choice(["csv", "json"]),
    help="Output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose (DEBUG) logging")
@click.option("--dry-run", is_flag=True, help="Validate inputs without making network requests")
@click.pass_context
def cli(
    ctx: click.Context,
    output: str,
    output_format: str,
    verbose: bool,
    dry_run: bool,
) -> None:
    """scrapers — Professional Multi-Platform Scraping CLI"""
    ctx.ensure_object(GlobalOptions)
    ctx.obj.output = output
    ctx.obj.format = output_format
    ctx.obj.verbose = verbose
    ctx.obj.dry_run = dry_run
    setup_logging(verbose)


# ════════════════════════════════════════════════════════════════════
# LinkedIn
# ════════════════════════════════════════════════════════════════════


@cli.command("linkedin")
@click.argument("urls", nargs=-1)
@click.option(
    "-f", "--file", "url_file", type=click.Path(exists=True), help="File with URLs (one per line)"
)
@click.option("-k", "--keyword", help="Keyword search via Google (site:linkedin.com/in)")
@click.option("--search-limit", type=int, default=10, help="Max results from keyword search")
@click.option("-d", "--delay", type=float, default=3.0, help="Delay between requests (seconds)")
@pass_opts
def cmd_linkedin(
    opts: GlobalOptions,
    urls: tuple[str, ...],
    url_file: str | None,
    keyword: str | None,
    search_limit: int,
    delay: float,
) -> None:
    """Scrape LinkedIn public profiles."""
    from src.models.linkedin import LinkedInProfile
    from src.scrapers.linkedin import LinkedInScraper
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would scrape[/cyan]")
        console.print(f"  URLs: {list(urls)}")
        console.print(f"  Keyword: {keyword}")
        return

    scraper = LinkedInScraper(delay=delay)

    all_urls: list[str] = list(urls)
    if url_file:
        with open(url_file) as f:
            all_urls.extend(line.strip() for line in f if line.strip())

    if keyword:
        found = scraper.search_by_keyword_google(keyword, limit=search_limit, delay=delay)
        all_urls.extend(found)
        console.print(f"[cyan]Keyword search found {len(found)} URLs[/cyan]")

    if not all_urls:
        console.print("[red]No URLs provided[/red]")
        return

    # Deduplicate
    seen: set[str] = set()
    unique: list[str] = []
    for u in all_urls:
        clean = u.split("?")[0].rstrip("/")
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(clean)

    console.print(f"[cyan]Scraping {len(unique)} profile(s)...[/cyan]")
    results: list[LinkedInProfile] = scraper.scrape_batch(unique).items

    if not results:
        console.print("[yellow]No profiles scraped successfully[/yellow]")
        return

    output = opts.output or "linkedin_profiles.csv"
    path = save_any(results, output, opts.format)
    console.print(f"[green]✓ Saved {len(results)} profiles → {path}[/green]")
    _print_table(results[:5], "LinkedIn Profiles")


# ════════════════════════════════════════════════════════════════════
# B2B Contact Finder
# ════════════════════════════════════════════════════════════════════


@cli.command("b2b")
@click.option("--domain", help="Company domain (e.g. acme.com)")
@click.option("--company", help="UK company name (Companies House — no API key needed)")
@click.option("--apollo-keyword", help="Apollo keyword search (e.g. 'sales manager')")
@click.option("--apollo-title", default="", help="Limit to specific job title")
@click.option("--country", default="", help="Limit to country code (e.g. GB)")
@click.option("--platform", type=click.Choice(["apollo", "hunter", "ch", "all"]), default="all")
@click.option("--company-number", help="UK company registration number (6-8 digits)")
@click.option("--officers", is_flag=True, help="Fetch officer/director list")
@click.option("-l", "--limit", type=int, default=10, help="Max results per source")
@pass_opts
def cmd_b2b(
    opts: GlobalOptions,
    domain: str | None,
    company: str | None,
    apollo_keyword: str | None,
    apollo_title: str,
    country: str,
    platform: str,
    company_number: str | None,
    officers: bool,
    limit: int,
) -> None:
    """B2B contact finder — Apollo.io, Hunter.io, Companies House UK."""
    from src.scrapers.b2b import B2BScraper
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would search[/cyan]")
        console.print(f"  domain={domain} company={company} keyword={apollo_keyword}")
        return

    scraper = B2BScraper()

    if company_number:
        if officers:
            officers_list = scraper.get_company_officers(company_number)
            output = opts.output or f"officers_{company_number}.json"
            save_any(officers_list, output, "json")
            console.print(f"[green]Saved {len(officers_list)} officers[/green]")
        else:
            details = scraper.get_company_details(company_number)
            output = opts.output or f"company_{company_number}.json"
            save_any([details], output, "json")
            console.print("[green]Saved company details[/green]")
        return

    if company:
        results = scraper.search_companies_house(company, items_per_page=limit)
        output = opts.output or f"uk_companies.{opts.format}"
        path = save_any(results, output, opts.format)
        console.print(f"[green]✓ Saved {len(results)} companies → {path}[/green]")
        return

    contacts: list = []
    if domain:
        if platform in ("apollo", "all"):
            contacts += scraper.search_apollo_by_domain(domain, limit=limit)
        if platform in ("hunter", "all"):
            contacts += scraper.search_hunter_by_domain(domain, limit=limit)

    elif apollo_keyword:
        contacts = scraper.search_apollo_by_keyword(
            apollo_keyword, title=apollo_title, country=country, limit=limit
        )

    else:
        console.print("[yellow]Provide --domain, --company, or --apollo-keyword[/yellow]")
        return

    if not contacts:
        console.print("[yellow]No contacts found[/yellow]")
        return

    output = opts.output or f"b2b_contacts.{opts.format}"
    path = save_any(contacts, output, opts.format)
    console.print(f"[green]✓ Saved {len(contacts)} contacts → {path}[/green]")


# ════════════════════════════════════════════════════════════════════
# Trip.com
# ════════════════════════════════════════════════════════════════════


@cli.command("trip")
@click.option(
    "--type", "trip_type", required=True, type=click.Choice(["flight", "hotel", "attraction"])
)
@click.option("--from", "depart", help="Departure airport IATA code (e.g. LHR)")
@click.option("--to", "arrive", help="Arrival airport IATA code")
@click.option("--date", help="Departure date (YYYY-MM-DD)")
@click.option("--return-date", default="", help="Return date (YYYY-MM-DD, round trips)")
@click.option("--city", help="City pinyin (e.g. london, shanghai)")
@click.option("--checkin", default="", help="Check-in date (YYYY-MM-DD)")
@click.option("--checkout", default="", help="Check-out date (YYYY-MM-DD)")
@click.option("--keyword", "-k", default="", help="Search keyword")
@click.option("--currency", default="CNY", help="Currency code")
@click.option("-d", "--delay", type=float, default=2.0)
@pass_opts
def cmd_trip(
    opts: GlobalOptions,
    trip_type: str,
    depart: str | None,
    arrive: str | None,
    date: str | None,
    return_date: str,
    city: str | None,
    checkin: str,
    checkout: str,
    keyword: str,
    currency: str,
    delay: float,
) -> None:
    """Scrape Trip.com — flights, hotels, attractions."""
    from src.scrapers.trip import TripScraper
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would search[/cyan]")
        console.print(f"  type={trip_type} city={city} depart={depart} arrive={arrive}")
        return

    scraper = TripScraper(delay=delay)
    results: list = []

    if trip_type == "flight":
        if not (depart and arrive and date):
            console.print("[red]--from, --to, and --date required for flights[/red]")
            return
        results = scraper.search_flights(depart, arrive, date, return_date, currency=currency)
        output = opts.output or "flights.csv"

    elif trip_type == "hotel":
        if not city:
            console.print("[red]--city required for hotels[/red]")
            return
        results = scraper.search_hotels(city, keyword, checkin, checkout, currency)
        output = opts.output or "hotels.csv"

    elif trip_type == "attraction":
        if not city:
            console.print("[red]--city required for attractions[/red]")
            return
        results = scraper.search_attractions(city, keyword, currency=currency)
        output = opts.output or "attractions.csv"

    if not results:
        console.print("[yellow]No results — page structure may have changed[/yellow]")
        return

    path = save_any(results, output, opts.format)
    console.print(f"[green]✓ Saved {len(results)} {trip_type} results → {path}[/green]")


# ════════════════════════════════════════════════════════════════════
# Amazon
# ════════════════════════════════════════════════════════════════════


@cli.command("amazon")
@click.option("--keyword", "-k", help="Search keyword")
@click.option("--asin", help="ASIN(s), comma-separated")
@click.option("--domain", type=click.Choice(["com", "co.uk"]), default="com")
@click.option("--pages", type=int, default=2, help="Number of result pages")
@click.option("-d", "--delay", type=float, default=3.0)
@click.option(
    "--browser/--no-browser",
    "use_browser",
    default=False,
    help="Use Playwright headless browser (bypasses anti-bot, slower but reliable)",
)
@pass_opts
def cmd_amazon(
    opts: GlobalOptions,
    keyword: str | None,
    asin: str | None,
    domain: str,
    pages: int,
    delay: float,
    use_browser: bool,
) -> None:
    """Scrape Amazon products by keyword or ASIN."""
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would scrape[/cyan]")
        console.print(f"  keyword={keyword} asin={asin} domain={domain} browser={use_browser}")
        return

    if not (keyword or asin):
        console.print("[yellow]Provide --keyword or --asin[/yellow]")
        return

    if use_browser:
        console.print("[cyan]Using Playwright headless browser...[/cyan]")
        from src.scrapers.amazon_browser import AmazonBrowserScraper

        scraper = AmazonBrowserScraper(domain=domain, delay=delay)
        try:
            if keyword:
                results = scraper.search(keyword, pages=pages)
                output = opts.output or f"amazon_{keyword[:20].replace(' ', '_')}.csv"
            else:
                assert asin is not None
                asins = [a.strip() for a in asin.split(",")]
                results = [r for r in [scraper.get_product(a) for a in asins] if r is not None]
                output = opts.output or "amazon_asins.csv"
        finally:
            scraper.close()
    else:
        from src.scrapers.amazon import AmazonScraper

        scraper = AmazonScraper(domain=domain, delay=delay)
        if keyword:
            results = scraper.search_by_keyword(keyword, pages=pages)
            output = opts.output or f"amazon_{keyword[:20].replace(' ', '_')}.csv"
        else:
            assert asin is not None
            asins = [a.strip() for a in asin.split(",")]
            results = scraper.scrape_batch(asins)
            output = opts.output or "amazon_asins.csv"

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    path = save_any(results, output, opts.format)
    console.print(f"[green]✓ Saved {len(results)} results → {path}[/green]")


# ════════════════════════════════════════════════════════════════════
# eBay
# ════════════════════════════════════════════════════════════════════


@cli.command("ebay")
@click.option("--search", help="Search keyword")
@click.option("--seller", help="Seller ID(s), comma-separated")
@click.option("--category", default="", help="Category ID")
@click.option("--condition", default="", help="Condition (new, used)")
@click.option("--max-price", default="", help="Maximum price")
@click.option("--min-price", default="", help="Minimum price")
@click.option(
    "--sort",
    type=click.Choice(["best_match", "price_asc", "price_desc", "newly_listed"]),
    default="best_match",
)
@click.option("--limit", type=int, default=50)
@click.option("-d", "--delay", type=float, default=2.0)
@pass_opts
def cmd_ebay(
    opts: GlobalOptions,
    search: str | None,
    seller: str | None,
    category: str,
    condition: str,
    max_price: str,
    min_price: str,
    sort: str,
    limit: int,
    delay: float,
) -> None:
    """Scrape eBay products or seller profiles."""
    from src.scrapers.ebay import EbayScraper
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would scrape[/cyan]")
        return

    scraper = EbayScraper(delay=delay)

    if seller:
        seller_ids = [s.strip() for s in seller.split(",")]
        results = scraper.fetch_sellers(seller_ids)
        output = opts.output or "ebay_sellers.csv"

    elif search:
        results = scraper.search_items(
            search, category, condition, max_price, min_price, sort, limit
        )
        output = opts.output or f"ebay_{search[:20].replace(' ', '_')}.csv"

    else:
        console.print("[yellow]Provide --search or --seller[/yellow]")
        return

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    path = save_any(results, output, opts.format)
    console.print(f"[green]✓ Saved {len(results)} results → {path}[/green]")


# ════════════════════════════════════════════════════════════════════
# AliExpress
# ════════════════════════════════════════════════════════════════════


@cli.command("aliexpress")
@click.argument("url", required=False)
@click.option("--keyword", "-k", help="Search keyword")
@click.option("--pages", type=int, default=1, help="Number of search result pages to scrape")
@click.option("--domain", type=click.Choice(["com", "ru", "id", "br"]), default="com")
@click.option("-d", "--delay", type=float, default=2.0)
@click.option(
    "--browser/--no-browser",
    "use_browser",
    default=False,
    help="Use Playwright headless browser (bypasses anti-bot, slower but more reliable)",
)
@pass_opts
def cmd_aliexpress(
    opts: GlobalOptions,
    url: str | None,
    keyword: str | None,
    pages: int,
    domain: str,
    delay: float,
    use_browser: bool,
) -> None:
    """Scrape AliExpress products — by URL (detail) or keyword (search)."""
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would scrape[/cyan]")
        console.print(f"  url={url} keyword={keyword} pages={pages} browser={use_browser}")
        return

    if use_browser:
        console.print("[cyan]Using Playwright headless browser...[/cyan]")
        try:
            from src.scrapers.aliexpress_browser import AliExpressBrowserScraper
        except ImportError:
            console.print("[red]aliexpress_browser not installed — run: pip install scrapers[browser][/red]")
            return

        scraper = AliExpressBrowserScraper(delay=delay)
        try:
            if url:
                results = [r for r in [scraper.get_product(url)] if r is not None]
                output = opts.output or "aliexpress_product.csv"
            else:
                if not keyword:
                    console.print("[yellow]Provide --keyword or a product URL[/yellow]")
                    return
                results = scraper.search(keyword, pages=pages)
                output = opts.output or f"aliexpress_{keyword[:20].replace(' ', '_')}.csv"
        finally:
            scraper.close()
    else:
        from src.scrapers.aliexpress import AliExpressScraper

        scraper = AliExpressScraper(delay=delay)

        if url:
            results = [r for r in [scraper.scrape_product(url)] if r is not None]
            output = opts.output or "aliexpress_product.csv"
        else:
            if not keyword:
                console.print("[yellow]Provide --keyword or a product URL[/yellow]")
                return
            results = scraper.scrape_search(keyword, pages=pages)
            output = opts.output or f"aliexpress_{keyword[:20].replace(' ', '_')}.csv"

    if not results:
        console.print("[yellow]No results — page structure may have changed or anti-bot blocked requests[/yellow]")
        return

    path = save_any(results, output, opts.format)
    console.print(f"[green]✓ Saved {len(results)} results → {path}[/green]")
    _print_table(results[:5], "AliExpress Products")


# ════════════════════════════════════════════════════════════════════
# Loyalty
# ════════════════════════════════════════════════════════════════════


@cli.command("loyalty")
@click.option("--nectar", is_flag=True, help="Query Nectar card balance")
@click.option("--tesco", is_flag=True, help="Query Tesco Clubcard balance")
@click.option("--amazon-gc", "amazon_gc", is_flag=True, help="Query Amazon gift card balance")
@click.option("--email", default="", help="Account email")
@click.option("--password", default="", help="Account password (use env var instead)")
@click.option("-o", "--output", default="loyalty_result.json")
@pass_opts
def cmd_loyalty(
    opts: GlobalOptions,
    nectar: bool,
    tesco: bool,
    amazon_gc: bool,
    email: str,
    password: str,
    output: str,
) -> None:
    """Check UK loyalty card balances — Nectar, Tesco Clubcard."""
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would check loyalty accounts[/cyan]")
        return

    # If no specific service chosen, default to nectar
    if not (nectar or tesco or amazon_gc):
        nectar = True

    email = email or input("\U0001f4e7 Email: ").strip()
    password = password or input("\U0001f510 Password: ").strip()

    scraper = __import__("src.scrapers.loyalty", fromlist=["LoyaltyScraper"]).LoyaltyScraper()
    results: dict[str, object] = {}

    if nectar:
        console.print("[cyan]Checking Nectar...[/cyan]")
        account = scraper.check_nectar(email, password)
        if account:
            results["nectar"] = account
            console.print(
                f"[green]Nectar: {account.points_balance} pts (~£{account.points_value})[/green]"
            )

    if tesco:
        console.print("[cyan]Checking Tesco Clubcard...[/cyan]")
        account = scraper.check_tesco(email, password)
        if account:
            results["tesco"] = account
            console.print(
                f"[green]Tesco: {account.points_balance} pts | Vouchers: £{account.vouchers_available}[/green]"
            )

    if amazon_gc:
        console.print("[cyan]Checking Amazon Gift Card...[/cyan]")
        gc = scraper.check_amazon_giftcard(email)
        if gc:
            results["amazon_giftcard"] = gc
            console.print(f"[green]Amazon GC Balance: {gc.balance}[/green]")

    if results:
        path = save_any(list(results.values()), output, "json")
        console.print(f"[green]✓ Saved → {path}[/green]")


# ════════════════════════════════════════════════════════════════════
# UK Supermarket
# ════════════════════════════════════════════════════════════════════


@cli.command("supermarket")
@click.option("--keyword", "-k", help="Search keyword")
@click.option(
    "--retailer", "-r", type=click.Choice(["john-lewis", "tesco", "ms", "all"]), default="all"
)
@click.option("--limit", "-l", type=int, default=30)
@click.option("--compare", "-c", is_flag=True, help="Compare across all retailers")
@click.option("-d", "--delay", type=float, default=2.0)
@click.option(
    "--browser/--no-browser",
    "use_browser",
    default=False,
    help="Use Playwright headless browser (recommended for Tesco, Amazon)",
)
@pass_opts
def cmd_supermarket(
    opts: GlobalOptions,
    keyword: str | None,
    retailer: str,
    limit: int,
    compare: bool,
    delay: float,
    use_browser: bool,
) -> None:
    """UK supermarket price comparison — John Lewis, Tesco, M&S."""
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would search[/cyan]")
        console.print(
            f"  keyword={keyword} retailer={retailer} compare={compare} browser={use_browser}"
        )
        return

    if use_browser and retailer in ("tesco", "all"):
        console.print("[cyan]Using Playwright headless browser for Tesco...[/cyan]")
        from src.scrapers.tesco_browser import TescoBrowserScraper

        tesco_scraper = TescoBrowserScraper(delay=delay)
        try:
            results = tesco_scraper.search(keyword or "milk", limit=limit)
        finally:
            tesco_scraper.close()
        output = opts.output or f"tesco_browser_{keyword or 'search'}.csv"
        if results:
            path = save_any(results, output, opts.format)
            console.print(f"[green]✓ Saved {len(results)} Tesco results → {path}[/green]")
        else:
            console.print("[yellow]No results found[/yellow]")
        return

    from src.scrapers.supermarket import SupermarketScraper

    scraper = SupermarketScraper(delay=delay)
    results: list = []
    keyword = keyword or ""

    if compare:
        results = scraper.compare_price(keyword, delay=delay)
        output = opts.output or f"supermarket_compare_{keyword or 'search'}.csv"

    elif retailer == "all":
        results = scraper.compare_price(keyword, delay=delay)
        output = opts.output or f"supermarket_all_{keyword}.csv"

    elif retailer == "john-lewis":
        if not keyword:
            console.print("[red]--keyword required[/red]")
            return
        results = scraper.search_john_lewis(keyword, limit=limit)
        output = opts.output or f"john_lewis_{keyword}.csv"

    elif retailer == "tesco":
        if not keyword:
            console.print("[red]--keyword required[/red]")
            return
        results = scraper.search_tesco(keyword, limit=limit)
        output = opts.output or f"tesco_{keyword}.csv"

    elif retailer == "ms":
        if not keyword:
            console.print("[red]--keyword required[/red]")
            return
        results = scraper.search_marks_and_spencer(keyword, limit=limit)
        output = opts.output or f"ms_{keyword}.csv"

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    path = save_any(results, output, opts.format)
    console.print(f"[green]✓ Saved {len(results)} results → {path}[/green]")


# ════════════════════════════════════════════════════════════════════
# Vinted
# ════════════════════════════════════════════════════════════════════


@cli.group("vinted")
def vinted():
    """Vinted European fashion resale marketplace (vinted.com)"""
    pass


@vinted.command("search")
@click.option("--keyword", "-k", "keyword", required=True, help="Search keyword")
@click.option("--pages", "-p", type=int, default=1, help="Number of result pages")
@click.option("--size", help="Filter by size (e.g. M, 38, 12)")
@click.option("--brand", help="Filter by brand name")
@click.option(
    "--condition",
    type=click.Choice(["new_with_tags", "new_without_tags", "very_good", "good", "satisfactory"]),
    help="Filter by item condition",
)
@click.option("--min-price", type=float, default=None, help="Minimum price")
@click.option("--max-price", type=float, default=None, help="Maximum price")
@click.option("--gender", type=click.Choice(["male", "female", "unisex"]), help="Gender filter")
@click.option("-d", "--delay", type=float, default=2.0)
@pass_opts
def vinted_search(
    opts: GlobalOptions,
    keyword: str,
    pages: int,
    size: str | None,
    brand: str | None,
    condition: str | None,
    min_price: float | None,
    max_price: float | None,
    gender: str | None,
    delay: float,
) -> None:
    """Search Vinted listings by keyword."""
    from src.scrapers.vinted import VintedScraper
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would search Vinted[/cyan]")
        console.print(
            f"  keyword={keyword} pages={pages} brand={brand} size={size} "
            f"condition={condition} min_price={min_price} max_price={max_price}"
        )
        return

    filters: dict = {}
    if brand:
        filters["brand"] = brand
    if size:
        filters["size"] = size
    if condition:
        filters["condition"] = condition
    if min_price is not None:
        filters["min_price"] = min_price
    if max_price is not None:
        filters["max_price"] = max_price
    if gender:
        filters["gender"] = gender

    scraper = VintedScraper(delay=delay)
    console.print(f"[cyan]Searching Vinted: '{keyword}' ({pages} page(s))[/cyan]")
    results = scraper.scrape_search(keyword, pages=pages, filters=filters or None)

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    output = opts.output or f"vinted_{keyword[:20].replace(' ', '_')}.csv"
    path = save_any(results, output, opts.format)
    console.print(f"[green]Saved {len(results)} results -> {path}[/green]")
    _print_table(results[:5], "Vinted Listings")


@vinted.command("product")
@click.argument("url")
@click.option("-d", "--delay", type=float, default=2.0)
@pass_opts
def vinted_product(
    opts: GlobalOptions,
    url: str,
    delay: float,
) -> None:
    """Get full details for a specific Vinted product URL."""
    from src.scrapers.vinted import VintedScraper
    from src.storage.writer import save_any

    if opts.dry_run:
        console.print("[cyan]Dry-run: would fetch Vinted product[/cyan]")
        console.print(f"  url={url}")
        return

    scraper = VintedScraper(delay=delay)
    console.print(f"[cyan]Fetching: {url}[/cyan]")
    product = scraper.scrape_product(url)

    if not product:
        console.print("[yellow]Could not retrieve product (blocked or not found)[/yellow]")
        return

    output = opts.output or "vinted_product.json"
    path = save_any([product], output, "json")
    console.print(f"[green]Saved 1 product -> {path}[/green]")
    _print_table([product], "Vinted Product")


# ─── Entry point ──────────────────────────────────────────────────


def main() -> None:
    """Installed as the `scrapers` console script."""
    cli(obj=GlobalOptions())


if __name__ == "__main__":
    main()
