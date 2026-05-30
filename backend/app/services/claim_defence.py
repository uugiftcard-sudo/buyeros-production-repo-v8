"""
Claim Defence — fake-claim detection + forbidden wording guard.

Scans product copy, captions, and descriptions for:
  - Forbidden words (legal / platform-policy violations)
  - Misleading authenticity claims
  - Price manipulation language
  - Prohibited comparison language

Also implements the Founder Approval Gate:
  - Any scan with severity CRITICAL or 2+ HIGH violations → gate triggers
  - Gate generates a structured approval request payload

Usage:
    from app.services.claim_defence import scan_text, FounderApprovalGate

    result = scan_text("100% authentic replica watch — lowest price guaranteed!")
    if result.requires_founder_approval:
        payload = FounderApprovalGate.build_request(product, result)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Severity levels
# ---------------------------------------------------------------------------

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH     = "HIGH"
SEVERITY_MEDIUM   = "MEDIUM"
SEVERITY_LOW      = "LOW"

SEVERITY_ORDER = {SEVERITY_CRITICAL: 4, SEVERITY_HIGH: 3, SEVERITY_MEDIUM: 2, SEVERITY_LOW: 1}

# ---------------------------------------------------------------------------
# Forbidden word / pattern definitions
# ---------------------------------------------------------------------------

# Each entry: (pattern_str, severity, reason, suggested_replacement)
FORBIDDEN_PATTERNS: list[tuple[str, str, str, str]] = [
    # ── Replica / counterfeit language ──────────────────────────────────────
    (r"\breplica\b",          SEVERITY_CRITICAL, "Implies counterfeit goods. Illegal to sell replicas of luxury brands.", "pre-owned"),
    (r"\bfake\b",             SEVERITY_CRITICAL, "Explicit counterfeit claim. Platform ban risk.", "pre-owned"),
    (r"\bcounterfeit\b",      SEVERITY_CRITICAL, "Illegal goods reference.", "authenticated"),
    (r"\bcopy\b",             SEVERITY_HIGH,     "Ambiguous but often implies replica. Risky for luxury listings.", "original"),
    (r"\bdupe\b",             SEVERITY_HIGH,     "'Dupe' implies non-authentic version. Platform policy violation.", "original"),
    (r"\bknock.?off\b",       SEVERITY_CRITICAL, "Explicit counterfeit term.", "pre-owned original"),
    (r"\bAAA.?grade\b",       SEVERITY_CRITICAL, "Code for high-quality counterfeit. Platform ban risk.", "authenticated"),
    (r"\b1:1\b",              SEVERITY_CRITICAL, "'1:1' is a known code for exact replica. Platforms flag this.", "original"),
    (r"\bsuper.?fake\b",      SEVERITY_CRITICAL, "Explicit counterfeit community term.", "authenticated original"),

    # ── Misleading authenticity claims ──────────────────────────────────────
    (r"\b100\s*%\s*(real|genuine|authentic|original)\b", SEVERITY_HIGH,
     "Absolute authenticity claim without certificate reference is misleading.", "authenticated (certificate provided)"),
    (r"\bguaranteed\s+real\b", SEVERITY_HIGH,
     "Unqualified guarantee. Must link to proof or certificate.", "authenticated with certificate"),
    (r"\bdefinitely\s+(real|authentic|original)\b", SEVERITY_MEDIUM,
     "Definitive language without proof reference.", "authenticated"),
    (r"\btrust\s+me\b",        SEVERITY_MEDIUM,
     "Appeals to personal trust instead of evidence. Unconvincing and risky.", "see certificate below"),

    # ── Price manipulation / false urgency ──────────────────────────────────
    (r"\bwas\s+[£HK\$]\d+",  SEVERITY_MEDIUM,
     "Crossed-out 'was' pricing must be a genuine previous price, not inflated.", "retail price"),
    (r"\bnormal\s+price\b",   SEVERITY_MEDIUM,
     "Vague price reference. Specify 'original retail price'.", "original retail price"),
    (r"\bsteal\b",            SEVERITY_LOW,
     "Casual slang — not prohibited but sounds informal for luxury.", "exceptional value"),
    (r"\blast\s+one\b",       SEVERITY_LOW,
     "Only flag if stock > 1. Ensure inventory_quantity=1 if used.", ""),
    (r"\bflash\s+sale\b",     SEVERITY_LOW,
     "Flash sale claims need a genuine time-limited price change.", "limited offer"),

    # ── Platform policy ─────────────────────────────────────────────────────
    (r"\bfollow\s+for\s+giveaway\b", SEVERITY_MEDIUM,
     "Conditional follow-for-giveaway schemes violate TikTok policy.", "join our community"),
    (r"\bsubscribe\s+to\s+win\b",    SEVERITY_MEDIUM,
     "Subscription-for-prize violates platform rules.", ""),
    (r"\bdm\s+for\s+price\b",        SEVERITY_LOW,
     "Price withholding creates friction. Better to list full price.", "price shown above"),

    # ── Legal / consumer protection ─────────────────────────────────────────
    (r"\bno\s+returns?\b",     SEVERITY_HIGH,
     "Blanket 'no returns' violates UK Consumer Rights Act 2015 for online sales.", "returns accepted per our policy"),
    (r"\ball\s+sales\s+final\b", SEVERITY_HIGH,
     "Same as above — illegal for distance selling in UK.", "please see our returns policy"),
    (r"\bas.?is\b",            SEVERITY_MEDIUM,
     "'As-is' disclaimer does not override statutory consumer rights.", "condition described in listing"),

    # ── Competitor/brand targeting ──────────────────────────────────────────
    (r"\bbetter\s+than\s+\w+\b", SEVERITY_MEDIUM,
     "Comparative advertising claims need substantiation.", ""),
    (r"\bcheaper\s+than\s+\w+\b", SEVERITY_LOW,
     "Price comparison claims — ensure accuracy.", ""),
]

# Compile patterns once at import time
_COMPILED: list[tuple[re.Pattern, str, str, str, str]] = [
    (re.compile(pattern, re.IGNORECASE), pattern, severity, reason, fix)
    for pattern, severity, reason, fix in FORBIDDEN_PATTERNS
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    """A single detected violation in scanned text."""
    pattern: str
    matched_text: str
    severity: str
    reason: str
    suggested_fix: str
    position: int           # character offset in original text

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "matched_text": self.matched_text,
            "severity": self.severity,
            "reason": self.reason,
            "suggested_fix": self.suggested_fix,
            "position": self.position,
        }


@dataclass
class ScanResult:
    """Full scan result for a piece of text."""
    original_text: str
    violations: list[Violation]
    highest_severity: str | None
    violation_count: int
    critical_count: int
    high_count: int
    clean: bool                     # True if no violations
    requires_founder_approval: bool
    suggested_text: str             # best-effort cleaned version
    scanned_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "violations": [v.to_dict() for v in self.violations],
            "highest_severity": self.highest_severity,
            "violation_count": self.violation_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "clean": self.clean,
            "requires_founder_approval": self.requires_founder_approval,
            "suggested_text": self.suggested_text,
            "scanned_at": self.scanned_at,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _highest_severity(violations: list[Violation]) -> str | None:
    if not violations:
        return None
    return max(violations, key=lambda v: SEVERITY_ORDER.get(v.severity, 0)).severity


def _build_suggested_text(text: str, violations: list[Violation]) -> str:
    """
    Apply best-effort replacements for violations that have a suggested_fix.
    Replacements are applied from right to left to preserve offsets.
    """
    result = text
    # Sort violations by position descending so replacements don't shift offsets
    fixable = sorted(
        [v for v in violations if v.suggested_fix],
        key=lambda v: v.position,
        reverse=True,
    )
    for v in fixable:
        # Find the matched text at approximate position and replace
        result = re.sub(
            re.compile(v.pattern, re.IGNORECASE),
            v.suggested_fix,
            result,
            count=1,
        )
    if result != text:
        result = f"[AUTO-CLEANED] {result}"
    return result


def _requires_approval(violations: list[Violation]) -> bool:
    """
    Founder Approval Gate triggers when:
      - Any CRITICAL violation is found, OR
      - 2 or more HIGH violations are found.
    """
    critical = sum(1 for v in violations if v.severity == SEVERITY_CRITICAL)
    high = sum(1 for v in violations if v.severity == SEVERITY_HIGH)
    return critical > 0 or high >= 2


# ---------------------------------------------------------------------------
# Public scan API
# ---------------------------------------------------------------------------

def scan_text(text: str) -> ScanResult:
    """
    Scan a string of text for forbidden words and misleading claims.

    Args:
        text: Any free-form text (caption, description, ad copy, etc.)

    Returns:
        ScanResult with violations, severity summary, and suggested clean text.
    """
    violations: list[Violation] = []

    for compiled_pattern, raw_pattern, severity, reason, fix in _COMPILED:
        for match in compiled_pattern.finditer(text):
            violations.append(Violation(
                pattern=raw_pattern,
                matched_text=match.group(0),
                severity=severity,
                reason=reason,
                suggested_fix=fix,
                position=match.start(),
            ))

    # Deduplicate: keep only highest-severity violation per matched_text
    seen: dict[str, Violation] = {}
    for v in violations:
        key = v.matched_text.lower()
        if key not in seen or SEVERITY_ORDER.get(v.severity, 0) > SEVERITY_ORDER.get(seen[key].severity, 0):
            seen[key] = v
    violations = list(seen.values())
    violations.sort(key=lambda v: (-SEVERITY_ORDER.get(v.severity, 0), v.position))

    critical_count = sum(1 for v in violations if v.severity == SEVERITY_CRITICAL)
    high_count = sum(1 for v in violations if v.severity == SEVERITY_HIGH)

    return ScanResult(
        original_text=text,
        violations=violations,
        highest_severity=_highest_severity(violations),
        violation_count=len(violations),
        critical_count=critical_count,
        high_count=high_count,
        clean=len(violations) == 0,
        requires_founder_approval=_requires_approval(violations),
        suggested_text=_build_suggested_text(text, violations),
    )


def scan_product(product: dict[str, Any]) -> dict[str, Any]:
    """
    Scan all text fields of a product dict.
    Checks: title, brand (edge cases), and any description/notes field.

    Returns dict with per-field scan results and an aggregate summary.
    """
    fields_to_scan = {
        "title": product.get("title", ""),
        "description": product.get("description", ""),
        "notes": product.get("notes", ""),
        "caption": product.get("caption", ""),
    }

    results: dict[str, dict] = {}
    all_violations: list[Violation] = []

    for field_name, text in fields_to_scan.items():
        if not text:
            continue
        r = scan_text(text)
        results[field_name] = r.to_dict()
        all_violations.extend(r.violations)

    critical = sum(1 for v in all_violations if v.severity == SEVERITY_CRITICAL)
    high = sum(1 for v in all_violations if v.severity == SEVERITY_HIGH)

    return {
        "product_id": product.get("id", "unknown"),
        "product_title": product.get("title", ""),
        "field_results": results,
        "aggregate": {
            "total_violations": len(all_violations),
            "critical_count": critical,
            "high_count": high,
            "highest_severity": _highest_severity(all_violations),
            "requires_founder_approval": _requires_approval(all_violations),
            "clean": len(all_violations) == 0,
        },
    }


# ---------------------------------------------------------------------------
# Founder Approval Gate
# ---------------------------------------------------------------------------

class FounderApprovalGate:
    """
    Generates and validates Founder Approval requests.

    The gate is triggered when:
      - A product has ProofScore grade < B AND collection == luxury
      - OR a ScanResult has requires_founder_approval == True
      - OR manually triggered by an ops team member

    The approval payload is sent to the Telegram admin bot (TG ID 6906214576)
    via the existing Telegram Edge Function webhook.
    """

    FOUNDER_TELEGRAM_ID: int = 6906214576

    @staticmethod
    def build_request(
        product: dict[str, Any],
        scan_result: ScanResult | None = None,
        proof_score: dict[str, Any] | None = None,
        triggered_by: str = "system",
    ) -> dict[str, Any]:
        """
        Build a structured approval request payload.

        Args:
            product: Product dict.
            scan_result: ScanResult from scan_text() (optional).
            proof_score: ProofScore.to_dict() result (optional).
            triggered_by: Who/what triggered the gate ("system" | "ops" | "auto").

        Returns:
            Approval request dict ready to POST to Telegram webhook.
        """
        pid = product.get("id", "unknown")
        title = product.get("title", "Unknown")
        price = f"HK${product.get('price_hkd', 0):,.0f}"
        collection = product.get("collection", "unknown")
        brand = product.get("brand", "unknown")

        violations_summary = "None"
        if scan_result and scan_result.violations:
            lines = []
            for v in scan_result.violations[:5]:  # top 5
                lines.append(f"  [{v.severity}] \"{v.matched_text}\" — {v.reason}")
            violations_summary = "\n".join(lines)

        proof_grade = proof_score.get("grade", "N/A") if proof_score else "N/A"
        proof_total = proof_score.get("total", "N/A") if proof_score else "N/A"

        message = (
            f"🔐 *FOUNDER APPROVAL REQUIRED*\n\n"
            f"*Product:* {title}\n"
            f"*ID:* `{pid}`\n"
            f"*Brand:* {brand} | *Collection:* {collection}\n"
            f"*Price:* {price}\n\n"
            f"*Proof Score:* {proof_grade} ({proof_total}/100)\n"
            f"*Triggered by:* {triggered_by}\n\n"
            f"*Violations detected:*\n{violations_summary}\n\n"
            f"Reply `/approve {pid}` to approve listing.\n"
            f"Reply `/reject {pid} [reason]` to reject."
        )

        return {
            "type": "founder_approval_request",
            "product_id": pid,
            "product_title": title,
            "telegram_target_id": FounderApprovalGate.FOUNDER_TELEGRAM_ID,
            "message": message,
            "parse_mode": "Markdown",
            "metadata": {
                "triggered_by": triggered_by,
                "proof_grade": proof_grade,
                "proof_total": proof_total,
                "violation_count": len(scan_result.violations) if scan_result else 0,
                "critical_violations": scan_result.critical_count if scan_result else 0,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }

    @staticmethod
    def should_gate(
        scan_result: ScanResult | None = None,
        proof_score: dict[str, Any] | None = None,
        product: dict[str, Any] | None = None,
    ) -> bool:
        """
        Determine if the Founder Approval Gate should trigger.

        Returns True if ANY of these conditions are met:
          1. ScanResult.requires_founder_approval == True
          2. ProofScore grade is F or (C + luxury collection)
          3. Product is luxury AND authenticity_verified == False
        """
        if scan_result and scan_result.requires_founder_approval:
            return True

        if proof_score:
            grade = proof_score.get("grade", "F")
            collection = (product or {}).get("collection", "luxury").lower()
            if grade == "F":
                return True
            if grade == "C" and collection == "luxury":
                return True

        if product:
            is_luxury = product.get("collection", "").lower() == "luxury"
            not_verified = not product.get("authenticity_verified", False)
            if is_luxury and not_verified:
                return True

        return False


# ---------------------------------------------------------------------------
# Convenience: full product check
# ---------------------------------------------------------------------------

def full_check(
    product: dict[str, Any],
    caption: str = "",
    proof_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the complete claim defence pipeline on a product + optional caption.

    Steps:
      1. Scan product text fields
      2. Scan caption if provided
      3. Check Founder Approval Gate
      4. Return consolidated result

    Args:
        product: Product dict.
        caption: Additional text to scan (e.g. video caption or ad copy).
        proof_score: ProofScore.to_dict() from proof_score.score().

    Returns:
        Consolidated dict with field_scan, caption_scan,
        gate_triggered, and approval_request (if gate triggered).
    """
    field_scan = scan_product(product)

    caption_scan: dict[str, Any] | None = None
    caption_result: ScanResult | None = None
    if caption:
        caption_result = scan_text(caption)
        caption_scan = caption_result.to_dict()

    # Determine worst scan for gate evaluation
    worst_scan = caption_result
    if field_scan["aggregate"]["critical_count"] > (caption_result.critical_count if caption_result else 0):
        # Build a dummy ScanResult from field aggregate for gate check
        worst_scan = ScanResult(
            original_text="[field scan aggregate]",
            violations=[],
            highest_severity=field_scan["aggregate"]["highest_severity"],
            violation_count=field_scan["aggregate"]["total_violations"],
            critical_count=field_scan["aggregate"]["critical_count"],
            high_count=field_scan["aggregate"]["high_count"],
            clean=field_scan["aggregate"]["clean"],
            requires_founder_approval=field_scan["aggregate"]["requires_founder_approval"],
            suggested_text="",
        )

    gate_triggered = FounderApprovalGate.should_gate(
        scan_result=worst_scan,
        proof_score=proof_score,
        product=product,
    )

    approval_request: dict[str, Any] | None = None
    if gate_triggered:
        approval_request = FounderApprovalGate.build_request(
            product=product,
            scan_result=worst_scan,
            proof_score=proof_score,
            triggered_by="auto",
        )

    return {
        "product_id": product.get("id", "unknown"),
        "field_scan": field_scan,
        "caption_scan": caption_scan,
        "gate_triggered": gate_triggered,
        "approval_request": approval_request,
        "listing_blocked": gate_triggered,
    }
