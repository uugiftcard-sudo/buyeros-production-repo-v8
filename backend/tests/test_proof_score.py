"""Unit tests for proof_score service."""

from app.services.proof_score import score, GRADE_THRESHOLDS


class TestProofScore:
    def test_luxury_with_proof_images_gets_high_score(self):
        product = {
            "brand": "Louis Vuitton",
            "category": "bag",
            "condition": "excellent",
            "authenticity_verified": True,
            "proof_images": [
                "https://cdn.example.com/img1.jpg",
                "https://cdn.example.com/img2.jpg",
                "https://cdn.example.com/img3.jpg",
            ],
            "collection": "luxury",
            "price_hkd": 15000,
        }
        result = score(product)
        assert result.grade in ("A", "B", "C")
        assert result.total >= 50

    def test_no_authentication_no_images_gets_low_score(self):
        product = {
            "brand": "Nike",
            "category": "shoes",
            "condition": "used",
            "authenticity_verified": False,
            "proof_images": [],
            "collection": "budget",
            "price_hkd": 500,
        }
        result = score(product)
        assert result.grade in ("C", "D", "F")
        assert result.total < 70

    def test_unknown_brand_uses_tier3(self):
        product = {
            "brand": "UnknownBrandXYZ",
            "condition": "new",
            "authenticity_verified": False,
            "proof_images": [],
            "collection": "luxury",
            "price_hkd": 1000,
        }
        result = score(product)
        assert result.total > 0

    def test_missing_fields_use_defaults(self):
        product: dict = {}
        result = score(product)
        assert result.total >= 0
        assert result.grade in ("A", "B", "C", "D", "F")

    def test_grade_thresholds_sequential(self):
        assert GRADE_THRESHOLDS["A"] > GRADE_THRESHOLDS["B"]
        assert GRADE_THRESHOLDS["B"] > GRADE_THRESHOLDS["C"]
        assert GRADE_THRESHOLDS["C"] > GRADE_THRESHOLDS["F"]
