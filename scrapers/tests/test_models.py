"""Unit tests for Pydantic models."""


from src.models.amazon import ProductResult
from src.models.b2b import B2BContact, UKCompany
from src.models.base import BaseScrapedItem, HTTPError, ScrapeResult
from src.models.ebay import ItemResult, SellerResult
from src.models.linkedin import LinkedInProfile
from src.models.loyalty import GiftcardBalance, NectarAccount, TescoClubcard
from src.models.supermarket import SupermarketResult
from src.models.trip import AttractionResult, FlightResult, HotelResult


class TestBaseScrapedItem:
    """Tests for BaseScrapedItem."""

    def test_scraped_at_auto_populated(self):
        item = BaseScrapedItem()
        assert item.scraped_at != ""
        # Should be on the form YYYY-MM-DD HH:MM:SS
        assert len(item.scraped_at) == 19

    def test_to_csv_dict_none_to_empty_string(self):
        item = BaseScrapedItem()
        d = item.to_csv_dict()
        assert d["scraped_at"] != ""

    def test_to_csv_dict_with_values(self):
        item = BaseScrapedItem()
        d = item.to_csv_dict()
        assert isinstance(d, dict)


class TestLinkedInProfile:
    """Tests for LinkedInProfile model."""

    def test_valid_profile(self):
        p = LinkedInProfile(
            name="John Doe",
            headline="Software Engineer",
            company="Acme Corp",
            industry="Technology",
            location="London, UK",
            profile_url="https://linkedin.com/in/johndoe",
        )
        assert p.name == "John Doe"
        assert p.company == "Acme Corp"
        assert p.profile_url == "https://linkedin.com/in/johndoe"

    def test_defaults(self):
        p = LinkedInProfile()
        assert p.name == ""
        assert p.headline == ""
        assert p.company == ""
        assert p.about == ""


class TestB2BContact:
    """Tests for B2BContact model."""

    def test_valid_contact(self):
        c = B2BContact(
            full_name="Jane Smith",
            first_name="Jane",
            last_name="Smith",
            title="VP of Sales",
            company="TechCo",
            email="jane@example.com",
            source="apollo",
        )
        assert c.full_name == "Jane Smith"
        assert c.email == "jane@example.com"
        assert c.source == "apollo"

    def test_raw_data_dict(self):
        c = B2BContact(raw_data={"extra": "field"})
        assert c.raw_data == {"extra": "field"}


class TestUKCompany:
    """Tests for UKCompany model."""

    def test_valid_company(self):
        c = UKCompany(
            number="12345678",
            title="Acme Ltd",
            company_type="Private Limited Company",
            status="active",
            incorporation_date="2020-01-15",
        )
        assert c.number == "12345678"
        assert c.status == "active"


class TestAmazonProductResult:
    """Tests for ProductResult model."""

    def test_valid_product(self):
        p = ProductResult(
            asin="B09V3KXJPB",
            title="Wireless Headphones",
            price="$99.99",
            currency="USD",
            rating="4.5",
            review_count="1,234",
            best_seller_badge="Yes",
            amazon_choice="No",
        )
        assert p.asin == "B09V3KXJPB"
        assert "99.99" in p.price

    def test_badges_default_no(self):
        p = ProductResult()
        assert p.best_seller_badge == "No"
        assert p.amazon_choice == "No"


class TestEbayModels:
    """Tests for eBay models."""

    def test_item_result_defaults(self):
        i = ItemResult()
        assert i.currency == "USD"
        assert i.condition == ""

    def test_seller_result_defaults(self):
        s = SellerResult()
        assert s.business is False
        assert s.top_rated is False


class TestLoyaltyModels:
    """Tests for loyalty card models."""

    def test_nectar_account(self):
        n = NectarAccount(
            card_number="1234567890",
            points_balance="5000",
            points_value="25.00",
            tier="Nectar Everyday",
        )
        assert n.points_balance == "5000"
        assert "25" in n.points_value

    def test_tesco_clubcard(self):
        t = TescoClubcard(
            card_number="9876543210",
            points_balance="3000",
            vouchers_available="15.00",
        )
        assert t.points_balance == "3000"

    def test_giftcard_balance(self):
        g = GiftcardBalance(
            card_name="Amazon UK",
            balance="£50.00",
            currency="GBP",
            card_type="Amazon",
        )
        assert g.currency == "GBP"


class TestSupermarketResult:
    """Tests for SupermarketResult model."""

    def test_supermarket_defaults(self):
        r = SupermarketResult()
        assert r.currency == "GBP"
        assert r.retailer == ""

    def test_supermarket_full(self):
        r = SupermarketResult(
            name="Whole Milk 1L",
            brand="Tesco",
            price="£1.20",
            original_price="£1.50",
            unit_price="£1.20/L",
            promotion="Save £0.30",
            retailer="Tesco",
        )
        assert r.promotion == "Save £0.30"
        assert r.unit_price == "£1.20/L"


class TestTripModels:
    """Tests for Trip.com models."""

    def test_flight_result(self):
        f = FlightResult(
            airline="British Airways",
            flight_no="BA 123",
            depart_time="08:00",
            arrive_time="11:30",
            depart_airport="LHR",
            arrive_airport="NRT",
            duration="11h 30m",
            price="850",
            currency="CNY",
        )
        assert f.airline == "British Airways"
        assert f.depart_airport == "LHR"

    def test_hotel_result(self):
        h = HotelResult(
            name="Grand Hotel Tokyo",
            star_rating="5",
            user_rating="4.7",
            price="1200",
            has_breakfast="Yes",
            free_cancellation="Yes",
        )
        assert h.has_breakfast == "Yes"
        assert h.free_cancellation == "Yes"

    def test_attraction_result(self):
        a = AttractionResult(
            name="Tokyo Tower",
            category="Landmark",
            city="Tokyo",
            rating="4.5",
            ticket_price="1200",
        )
        assert a.category == "Landmark"


class TestHTTPError:
    """Tests for HTTPError model."""

    def test_http_error_with_status(self):
        e = HTTPError(url="https://example.com", status_code=403, error_message="Forbidden")
        assert e.status_code == 403
        assert e.error_message == "Forbidden"

    def test_http_error_defaults(self):
        e = HTTPError(url="https://example.com")
        assert e.status_code is None
        assert e.error_message == ""


class TestScrapeResult:
    """Tests for ScrapeResult generic model."""

    def test_scrape_result_items(self):
        r = ScrapeResult[LinkedInProfile](items=[LinkedInProfile(name="Test")])
        assert len(r.items) == 1

    def test_scrape_result_errors(self):
        e = HTTPError(url="https://fail.com", error_message="Timeout")
        r = ScrapeResult[LinkedInProfile](errors=[e])
        assert len(r.errors) == 1

    def test_scrape_result_success_rate(self):
        r = ScrapeResult[LinkedInProfile](total_requests=5, successful_requests=3)
        assert r.success_rate == 0.6
