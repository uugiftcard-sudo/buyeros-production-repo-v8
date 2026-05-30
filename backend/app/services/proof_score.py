"""
Proof Score — authenticity & quality scoring engine.

Evaluates a product dict and returns a structured score breakdown.

Usage:
    from app.services.proof_score import score, ProofScore

    result: ProofScore = score(product_dict)
    print(result.grade, result.total)   # e.g. "A", 88
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Weights (total = 100 points)
# ---------------------------------------------------------------------------

W_AUTH_VERIFIED       = 40   # authenticity_verified flag from Shopify/CLOTH
W_PROOF_IMAGES        = 20   # number and quality of proof images
W_CONDITION           = 15   # condition: new > vintage > used
W_BRAND_REPUTATION    = 15   # brand tier based on known brand lists
W_COLLECTION_MATCH    = 10   # collection tag consistency with price/brand

# Grade thresholds
GRADE_THRESHOLDS = {
    "A": 85,
    "B": 70,
    "C": 50,
    "F": 0,
}

# Brand reputation tiers
BRAND_TIER_1 = {
    "Louis Vuitton", "Chanel", "Hermès", "Hermes", "Rolex", "Patek Philippe",
    "Cartier", "Gucci", "Prada", "Dior", "Bottega Veneta", "Balenciaga",
    "Saint Laurent", "Celine", "Givenchy", "Fendi", "Burberry", "Moncler",
    "Canada Goose",
}
BRAND_TIER_2 = {
    "Coach", "Michael Kors", "Kate Spade", "Tory Burch", "Marc Jacobs",
    "Longchamp", "Mulberry", "Ted Baker", "Vivienne Westwood",
    "Alexander Wang", "Versace", "Valentino", "Off-White", "Acne Studios",
}
BRAND_TIER_3 = {
    "Nike", "Adidas", "New Balance", "Puma", "Asics", "Converse",
    "Vans", "Under Armour", "Reebok", "Jordan",
}

# Luxury collections that should require higher verification
HIGH_STAKES_COLLECTIONS = {"luxury"}

# Minimum recommended proof images per tier
MIN_IMAGES_LUXURY  = 5
MIN_IMAGES_BUDGET  = 2

# Condition scoring
CONDITION_SCORES = {
    "new":     15,
    "vintage": 12,
    "used":    8,
}

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ScoreComponent:
    """A single scoring dimension."""
    name: str
    label: str
    raw_score: int          # points earned
    max_score: int          # max possible points
    pct: float              # raw_score / max_score * 100
    passed: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "raw_score": self.raw_score,
            "max_score": self.max_score,
            "pct": round(self.pct, 1),
            "passed": self.passed,
            "notes": self.notes,
        }


@dataclass
class ProofScore:
    """Full proof score result for a product."""
    product_id: str
    product_title: str
    total: int                          # 0–100
    grade: str                          # A | B | C | F
    components: list[ScoreComponent]
    recommendations: list[str]
    requires_founder_approval: bool     # True when grade < B on luxury
    listing_safe: bool                  # True when grade >= C

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_title": self.product_title,
            "total": self.total,
            "grade": self.grade,
            "components": [c.to_dict() for c in self.components],
            "recommendations": self.recommendations,
            "requires_founder_approval": self.requires_founder_approval,
            "listing_safe": self.listing_safe,
        }


# ---------------------------------------------------------------------------
# Internal scorers
# ---------------------------------------------------------------------------

def _score_auth_verified(product: dict[str, Any]) -> ScoreComponent:
    verified: bool = bool(product.get("authenticity_verified", False))
    raw = W_AUTH_VERIFIED if verified else 0
    pct = (raw / W_AUTH_VERIFIED) * 100
    notes = (
        "Authenticity verified flag set — full points awarded."
        if verified else
        "Not marked as authenticated. Set authenticity_verified=True after third-party check."
    )
    return ScoreComponent(
        name="auth_verified",
        label="Authenticity Verified",
        raw_score=raw,
        max_score=W_AUTH_VERIFIED,
        pct=pct,
        passed=verified,
        notes=notes,
    )


def _score_proof_images(product: dict[str, Any]) -> ScoreComponent:
    images: list = product.get("proof_images", [])
    n = len(images)
    collection = product.get("collection", "luxury").lower()
    is_luxury = collection in HIGH_STAKES_COLLECTIONS
    min_required = MIN_IMAGES_LUXURY if is_luxury else MIN_IMAGES_BUDGET

    if n == 0:
        raw = 0
        notes = f"No proof images. Minimum required: {min_required}."
    elif n < min_required:
        # Partial credit
        raw = int(W_PROOF_IMAGES * (n / min_required) * 0.7)
        notes = f"{n} image(s) provided. Recommend at least {min_required} for this collection."
    elif n < min_required + 3:
        raw = int(W_PROOF_IMAGES * 0.85)
        notes = f"{n} images — good. Add {min_required + 3 - n} more for full marks."
    else:
        raw = W_PROOF_IMAGES
        notes = f"{n} proof images — excellent coverage."

    pct = (raw / W_PROOF_IMAGES) * 100
    return ScoreComponent(
        name="proof_images",
        label="Proof Images",
        raw_score=raw,
        max_score=W_PROOF_IMAGES,
        pct=pct,
        passed=(raw >= int(W_PROOF_IMAGES * 0.5)),
        notes=notes,
    )


def _score_condition(product: dict[str, Any]) -> ScoreComponent:
    condition: str = product.get("condition", "used").lower()
    raw = CONDITION_SCORES.get(condition, 8)
    pct = (raw / W_CONDITION) * 100
    notes = f"Condition: {condition.capitalize()} — {raw}/{W_CONDITION} points."
    return ScoreComponent(
        name="condition",
        label="Condition",
        raw_score=raw,
        max_score=W_CONDITION,
        pct=pct,
        passed=True,
        notes=notes,
    )


def _score_brand_reputation(product: dict[str, Any]) -> ScoreComponent:
    brand: str = product.get("brand", "")
    if brand in BRAND_TIER_1:
        raw = W_BRAND_REPUTATION
        tier = "Tier 1 (ultra-luxury)"
    elif brand in BRAND_TIER_2:
        raw = int(W_BRAND_REPUTATION * 0.8)
        tier = "Tier 2 (accessible luxury)"
    elif brand in BRAND_TIER_3:
        raw = int(W_BRAND_REPUTATION * 0.65)
        tier = "Tier 3 (premium sportswear)"
    else:
        raw = int(W_BRAND_REPUTATION * 0.4)
        tier = f"Unknown brand '{brand}' — manual review recommended"
    pct = (raw / W_BRAND_REPUTATION) * 100
    return ScoreComponent(
        name="brand_reputation",
        label="Brand Reputation",
        raw_score=raw,
        max_score=W_BRAND_REPUTATION,
        pct=pct,
        passed=(raw >= int(W_BRAND_REPUTATION * 0.5)),
        notes=tier,
    )


def _score_collection_match(product: dict[str, Any]) -> ScoreComponent:
    """
    Check that the product's collection tag is consistent with its brand and price.
    Luxury brands in the budget collection or vice versa lose points.
    """
    brand: str = product.get("brand", "")
    collection: str = product.get("collection", "").lower()
    price_hkd: float = float(product.get("price_hkd", 0))

    issues: list[str] = []

    if brand in BRAND_TIER_1 and collection != "luxury":
        issues.append(f"{brand} is a Tier-1 luxury brand but collection is '{collection}'. Should be 'luxury'.")
    if brand in BRAND_TIER_3 and collection == "luxury":
        issues.append(f"{brand} is a sportswear brand but collection is 'luxury'. Consider 'budget'.")
    if collection == "luxury" and price_hkd < 1000:
        issues.append(f"Price HK${price_hkd:,.0f} seems low for a luxury collection item. Verify pricing.")
    if collection == "budget" and price_hkd > 15000:
        issues.append(f"Price HK${price_hkd:,.0f} seems high for a budget collection item. Verify pricing.")

    if not issues:
        raw = W_COLLECTION_MATCH
        notes = "Collection tag consistent with brand and price."
    else:
        raw = 0
        notes = " | ".join(issues)

    pct = (raw / W_COLLECTION_MATCH) * 100
    return ScoreComponent(
        name="collection_match",
        label="Collection Consistency",
        raw_score=raw,
        max_score=W_COLLECTION_MATCH,
        pct=pct,
        passed=(not issues),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Grade resolver
# ---------------------------------------------------------------------------

def _resolve_grade(total: int) -> str:
    if total >= GRADE_THRESHOLDS["A"]:
        return "A"
    if total >= GRADE_THRESHOLDS["B"]:
        return "B"
    if total >= GRADE_THRESHOLDS["C"]:
        return "C"
    return "F"


# ---------------------------------------------------------------------------
# Recommendations builder
# ---------------------------------------------------------------------------

def _build_recommendations(
    components: list[ScoreComponent],
    grade: str,
    product: dict[str, Any],
) -> list[str]:
    recs: list[str] = []
    for c in components:
        if not c.passed:
            recs.append(f"[{c.label}] {c.notes}")

    collection = product.get("collection", "luxury").lower()
    if grade == "F":
        recs.insert(0, "🔴 CRITICAL: Do NOT list this product until score reaches grade C or above.")
    elif grade == "C":
        recs.insert(0, "🟡 CAUTION: Listing allowed but Founder Approval required before going live.")
    elif grade == "B" and collection in HIGH_STAKES_COLLECTIONS:
        recs.insert(0, "🟡 Grade B on luxury item — review proof images before listing.")

    if not recs:
        recs.append("✅ All checks passed — product is ready to list.")
    return recs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score(product: dict[str, Any]) -> ProofScore:
    """
    Score a product for authenticity and listing readiness.

    Args:
        product: Product dict. Expected keys:
            id, title, brand, category, collection,
            price_hkd, condition, authenticity_verified, proof_images.

    Returns:
        ProofScore dataclass with full breakdown.
    """
    components = [
        _score_auth_verified(product),
        _score_proof_images(product),
        _score_condition(product),
        _score_brand_reputation(product),
        _score_collection_match(product),
    ]

    total = sum(c.raw_score for c in components)
    grade = _resolve_grade(total)
    collection = product.get("collection", "luxury").lower()
    is_luxury = collection in HIGH_STAKES_COLLECTIONS

    # Founder approval: required for luxury grade < B, or any grade F
    requires_approval = (grade == "F") or (is_luxury and grade == "C")
    listing_safe = grade in ("A", "B") or (grade == "C" and not is_luxury)

    recs = _build_recommendations(components, grade, product)

    return ProofScore(
        product_id=product.get("id", "unknown"),
        product_title=product.get("title", "Unknown"),
        total=total,
        grade=grade,
        components=components,
        recommendations=recs,
        requires_founder_approval=requires_approval,
        listing_safe=listing_safe,
    )


def score_batch(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score a list of products. Returns list of ProofScore dicts."""
    return [score(p).to_dict() for p in products]


def summary_stats(scores: list[ProofScore]) -> dict[str, Any]:
    """Aggregate stats across a batch of ProofScore results."""
    if not scores:
        return {"count": 0}
    totals = [s.total for s in scores]
    grade_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "F": 0}
    for s in scores:
        grade_counts[s.grade] = grade_counts.get(s.grade, 0) + 1
    return {
        "count": len(scores),
        "average_score": round(sum(totals) / len(totals), 1),
        "min_score": min(totals),
        "max_score": max(totals),
        "grade_distribution": grade_counts,
        "listing_safe_count": sum(1 for s in scores if s.listing_safe),
        "requires_founder_approval_count": sum(1 for s in scores if s.requires_founder_approval),
    }
