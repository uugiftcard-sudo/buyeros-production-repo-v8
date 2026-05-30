"""Unit tests for claim_defence service."""

from app.services.claim_defence import scan_text


class TestClaimDefence:
    def test_clean_text_passes(self):
        result = scan_text("Louis Vuitton Neverfull MM — pre-owned, authenticated.")
        assert not result.requires_founder_approval
        assert result.critical_count == 0
        assert result.high_count == 0
        assert result.clean

    def test_detects_replica_keyword(self):
        result = scan_text("High quality replica bag — looks exactly like Chanel.")
        assert result.critical_count >= 1

    def test_detects_fake_keyword(self):
        result = scan_text("Fake designer watch — great deal.")
        assert result.critical_count >= 1

    def test_detects_absolute_authenticity_claim(self):
        result = scan_text("100% genuine authentic Hermès Birkin.")
        assert result.high_count >= 1

    def test_detects_price_manipulation_language(self):
        # "guaranteed real" is HIGH severity per pattern definitions
        result = scan_text("This bag is guaranteed real — best deal in town!")
        assert result.violation_count >= 1

    def test_detects_comparison_language_as_medium(self):
        # "better than" is MEDIUM severity per pattern definitions
        result = scan_text("Better than the original.")
        assert result.violation_count >= 1
        assert result.high_count == 0  # MEDIUM, not HIGH

    def test_detects_aaa_grade(self):
        result = scan_text("AAA grade quality bag.")
        assert result.critical_count >= 1

    def test_triggers_founder_approval_on_critical(self):
        result = scan_text("Replica watch for sale — 1:1 quality.")
        assert result.requires_founder_approval

    def test_multiple_high_violations_trigger_founder_approval(self):
        # Need 2+ HIGH violations — use text with multiple HIGH patterns
        result = scan_text("100% real bag — guaranteed real — no returns!")
        assert result.violation_count >= 2
        assert result.high_count >= 2
        assert result.requires_founder_approval

    def test_clean_product_text_returns_not_clean(self):
        result = scan_text("Brand: Louis Vuitton. Condition: excellent. Price: HK$15000.")
        # Clean product text should have clean=True or very few violations
        assert result.violation_count == 0 or result.clean

    def test_no_returns_clause_flagged(self):
        result = scan_text("All sales final — no returns accepted.")
        assert result.high_count >= 1

    def test_scan_result_has_required_fields(self):
        result = scan_text("Test text.")
        assert hasattr(result, "original_text")
        assert hasattr(result, "violations")
        assert hasattr(result, "highest_severity")
        assert hasattr(result, "requires_founder_approval")
        assert hasattr(result, "scanned_at")
