"""
TikTok Shop / Creator connector — mock mode by default.

Real mode activates when both env vars are present:
  TIKTOK_ACCESS_TOKEN
  TIKTOK_APP_ID

Mock mode: in-memory content generation, no external calls.
Real mode: raises NotImplementedError until TikTok API is wired.

Generators:
  generate_video_pack(product, market)  → structured content pack
  build_live_script(products, duration_mins, market) → live stream script
  build_ads_brief(product, objective, budget_hkd, market) → ads creative brief
"""

from __future__ import annotations

import os
import random
import textwrap
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Config / mock-mode gate
# ---------------------------------------------------------------------------

TIKTOK_ACCESS_TOKEN: str = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_APP_ID: str = os.getenv("TIKTOK_APP_ID", "")

MOCK_MODE: bool = not (TIKTOK_ACCESS_TOKEN and TIKTOK_APP_ID)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

CURRENCY_SYMBOL: dict[str, str] = {"hkd": "HK$", "gbp": "£"}

HK_HASHTAGS_LUXURY = [
    "#名牌二手", "#二手奢侈品", "#正品保證", "#HKVintage", "#LuxuryHK",
    "#PreOwned", "#Authenticated", "#BuyerOS", "#名牌", "#香港二手",
]
HK_HASHTAGS_BUDGET = [
    "#球鞋控", "#潮牌", "#香港球鞋", "#HKSneaker", "#StreetFashion",
    "#BudgetLux", "#SneakerHK", "#球鞋市場", "#BuyerOS",
]
UK_HASHTAGS_LUXURY = [
    "#LuxuryResale", "#PreOwnedLuxury", "#AuthenticLuxury", "#UKFashion",
    "#DesignerHandbag", "#LuxuryWatch", "#SecondHandLuxury", "#BuyerOS",
    "#LondonFashion", "#SustainableLuxury",
]
UK_HASHTAGS_BUDGET = [
    "#UKSneakers", "#SneakerCommunity", "#StreetStyleUK", "#TrainersUK",
    "#SneakerHead", "#BudgetFashion", "#UKFashion", "#BuyerOS",
]

VIDEO_FORMATS = ["vertical_9x16", "square_1x1", "horizontal_16x9"]
VIDEO_DURATIONS = {
    "short": "15-30s",
    "medium": "30-60s",
    "long": "60-180s",
}

LIVE_SEGMENT_DURATION_MINS = 8   # minutes per product segment in a live
LIVE_INTRO_MINS = 3
LIVE_OUTRO_MINS = 2

ADS_OBJECTIVES = [
    "traffic", "conversion", "product_sales",
    "reach", "video_views", "lead_generation",
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class VideoHook:
    """Opening hook variant for a video."""
    type: str       # question | shock | story | challenge
    text: str
    duration_s: int = 3


@dataclass
class VideoCaption:
    """Caption / description for a video post."""
    headline: str
    body: str
    cta: str
    full_text: str = field(init=False)

    def __post_init__(self) -> None:
        self.full_text = f"{self.headline}\n\n{self.body}\n\n{self.cta}"


@dataclass
class VideoPack:
    """Complete content pack for one product video."""
    product_id: str
    product_title: str
    market: str
    hooks: list[VideoHook]
    caption: VideoCaption
    hashtags: list[str]
    recommended_format: str
    recommended_duration: str
    talking_points: list[str]
    b_roll_suggestions: list[str]
    music_vibe: str
    posting_time_suggestion: str
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_title": self.product_title,
            "market": self.market,
            "hooks": [
                {"type": h.type, "text": h.text, "duration_s": h.duration_s}
                for h in self.hooks
            ],
            "caption": {
                "headline": self.caption.headline,
                "body": self.caption.body,
                "cta": self.caption.cta,
                "full_text": self.caption.full_text,
            },
            "hashtags": self.hashtags,
            "recommended_format": self.recommended_format,
            "recommended_duration": self.recommended_duration,
            "talking_points": self.talking_points,
            "b_roll_suggestions": self.b_roll_suggestions,
            "music_vibe": self.music_vibe,
            "posting_time_suggestion": self.posting_time_suggestion,
            "generated_at": self.generated_at,
        }


@dataclass
class LiveSegment:
    """One product segment within a TikTok Live script."""
    segment_no: int
    product_id: str
    product_title: str
    price_display: str
    duration_mins: int
    intro_line: str
    key_points: list[str]
    authenticity_pitch: str
    urgency_line: str
    cta_line: str


@dataclass
class LiveScript:
    """Full TikTok Live streaming script."""
    market: str
    total_duration_mins: int
    intro: str
    segments: list[LiveSegment]
    outro: str
    engagement_prompts: list[str]   # mid-stream audience interaction lines
    pinned_comment_suggestion: str
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "total_duration_mins": self.total_duration_mins,
            "intro": self.intro,
            "segments": [
                {
                    "segment_no": s.segment_no,
                    "product_id": s.product_id,
                    "product_title": s.product_title,
                    "price_display": s.price_display,
                    "duration_mins": s.duration_mins,
                    "intro_line": s.intro_line,
                    "key_points": s.key_points,
                    "authenticity_pitch": s.authenticity_pitch,
                    "urgency_line": s.urgency_line,
                    "cta_line": s.cta_line,
                }
                for s in self.segments
            ],
            "outro": self.outro,
            "engagement_prompts": self.engagement_prompts,
            "pinned_comment_suggestion": self.pinned_comment_suggestion,
            "generated_at": self.generated_at,
        }


@dataclass
class AdsBrief:
    """TikTok ads creative brief for one product."""
    product_id: str
    product_title: str
    market: str
    objective: str
    budget_hkd: float
    budget_gbp: float
    target_audience: dict[str, Any]
    creative_direction: str
    primary_copy: str
    secondary_copy: str
    cta_button: str
    landing_page_suggestion: str
    budget_split: dict[str, Any]
    kpi_targets: dict[str, Any]
    dos: list[str]
    donts: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_title": self.product_title,
            "market": self.market,
            "objective": self.objective,
            "budget_hkd": self.budget_hkd,
            "budget_gbp": self.budget_gbp,
            "target_audience": self.target_audience,
            "creative_direction": self.creative_direction,
            "primary_copy": self.primary_copy,
            "secondary_copy": self.secondary_copy,
            "cta_button": self.cta_button,
            "landing_page_suggestion": self.landing_page_suggestion,
            "budget_split": self.budget_split,
            "kpi_targets": self.kpi_targets,
            "dos": self.dos,
            "donts": self.donts,
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class TikTokAPINotConfiguredError(Exception):
    """Raised when real API is requested but env vars are missing."""


class TikTokAPIError(Exception):
    """Raised when the TikTok API returns an error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _price_display(product: dict[str, Any], market: str) -> str:
    """Return formatted price string for the given market."""
    m = market.lower()
    if m == "uk":
        return f"£{product.get('price_gbp', 0):,.2f}"
    return f"HK${product.get('price_hkd', 0):,.0f}"


def _is_luxury(product: dict[str, Any]) -> bool:
    return product.get("collection", "").lower() == "luxury"


def _hashtags_for(product: dict[str, Any], market: str) -> list[str]:
    luxury = _is_luxury(product)
    if market.lower() == "uk":
        base = UK_HASHTAGS_LUXURY if luxury else UK_HASHTAGS_BUDGET
    else:
        base = HK_HASHTAGS_LUXURY if luxury else HK_HASHTAGS_BUDGET

    brand_tag = f"#{product.get('brand', '').replace(' ', '')}"
    category_tag = f"#{product.get('category', '').capitalize()}"
    extra = [brand_tag, category_tag]
    combined = base + extra
    random.shuffle(combined)
    return combined[:12]


def _music_vibe(product: dict[str, Any]) -> str:
    luxury = _is_luxury(product)
    if luxury:
        return "Elegant orchestral / lo-fi jazz — premium feel, no vocals"
    return "Upbeat hip-hop / trap — energetic, trend-forward"


def _posting_time(market: str) -> str:
    if market.lower() == "uk":
        return "19:00–21:00 GMT (weekday) / 11:00–13:00 GMT (weekend)"
    return "20:00–22:00 HKT (weekday) / 12:00–14:00 HKT (weekend)"


def _audience_for(product: dict[str, Any], market: str) -> dict[str, Any]:
    luxury = _is_luxury(product)
    if market.lower() == "uk":
        if luxury:
            return {
                "age_range": "25-45",
                "gender": "female_skewed",
                "interests": ["luxury fashion", "designer handbags", "fine watches", "sustainable fashion"],
                "income_bracket": "high",
                "geo": "United Kingdom",
                "custom_audiences": ["website_visitors", "video_viewers_25pct"],
                "lookalike": "top_purchasers_uk",
            }
        return {
            "age_range": "18-34",
            "gender": "male_skewed",
            "interests": ["sneakers", "streetwear", "hype culture", "sports"],
            "income_bracket": "mid",
            "geo": "United Kingdom",
            "custom_audiences": ["add_to_cart_no_purchase"],
            "lookalike": "sneaker_buyers_uk",
        }
    # HK
    if luxury:
        return {
            "age_range": "28-50",
            "gender": "female_skewed",
            "interests": ["名牌", "二手奢侈品", "fashion", "daigou"],
            "income_bracket": "high",
            "geo": "Hong Kong",
            "custom_audiences": ["website_visitors", "engagement_followers"],
            "lookalike": "top_buyers_hk",
        }
    return {
        "age_range": "18-30",
        "gender": "mixed",
        "interests": ["球鞋", "streetwear", "潮流", "limited edition"],
        "income_bracket": "mid",
        "geo": "Hong Kong",
        "custom_audiences": ["video_viewers_50pct"],
        "lookalike": "sneaker_buyers_hk",
    }


def _kpi_targets(objective: str, budget_hkd: float) -> dict[str, Any]:
    """Indicative KPI targets based on objective and budget."""
    base: dict[str, Any] = {}
    if objective in ("conversion", "product_sales"):
        base = {
            "target_roas": "3.5x",
            "target_cpa_hkd": round(budget_hkd * 0.05, 0),
            "target_ctr": "2.5%",
            "target_conversion_rate": "1.8%",
        }
    elif objective == "traffic":
        base = {
            "target_cpc_hkd": round(budget_hkd * 0.02, 1),
            "target_ctr": "3%",
            "target_sessions": int(budget_hkd / 2),
        }
    elif objective == "video_views":
        base = {
            "target_cpv_hkd": 0.05,
            "target_view_rate": "20%",
            "target_views": int(budget_hkd / 0.05),
        }
    elif objective == "reach":
        base = {
            "target_cpm_hkd": round(budget_hkd * 0.03, 1),
            "target_reach": int(budget_hkd * 30),
            "target_frequency": "2.5",
        }
    else:
        base = {
            "target_cpl_hkd": round(budget_hkd * 0.08, 0),
            "target_leads": int(budget_hkd / 8),
        }
    return base


def _budget_split(budget_hkd: float, objective: str) -> dict[str, Any]:
    """Recommended budget split across ad formats."""
    if objective in ("conversion", "product_sales"):
        return {
            "in_feed_ads_pct": 50,
            "spark_ads_pct": 30,
            "top_view_pct": 0,
            "collection_ads_pct": 20,
            "in_feed_ads_hkd": round(budget_hkd * 0.50, 0),
            "spark_ads_hkd": round(budget_hkd * 0.30, 0),
            "collection_ads_hkd": round(budget_hkd * 0.20, 0),
        }
    elif objective == "video_views":
        return {
            "in_feed_ads_pct": 40,
            "spark_ads_pct": 60,
            "in_feed_ads_hkd": round(budget_hkd * 0.40, 0),
            "spark_ads_hkd": round(budget_hkd * 0.60, 0),
        }
    else:
        return {
            "in_feed_ads_pct": 70,
            "spark_ads_pct": 30,
            "in_feed_ads_hkd": round(budget_hkd * 0.70, 0),
            "spark_ads_hkd": round(budget_hkd * 0.30, 0),
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_video_pack(
    product: dict[str, Any],
    market: str = "hk",
) -> dict[str, Any]:
    """
    Generate a structured video content pack for a product.

    Args:
        product: Product dict (from shopify_connector.ShopifyProduct.to_dict()
                 or any dict with keys: id, title, brand, category,
                 collection, price_hkd, price_gbp, condition,
                 authenticity_verified).
        market: "hk" | "uk"

    Returns:
        VideoPack.to_dict()
    """
    if not MOCK_MODE:
        raise NotImplementedError(
            "Real TikTok Creator API not yet wired. "
            "Set TIKTOK_ACCESS_TOKEN + TIKTOK_APP_ID to activate real mode, "
            "then implement the API call here."
        )

    pid = product.get("id", "unknown")
    title = product.get("title", "Unknown Product")
    brand = product.get("brand", "")
    category = product.get("category", "item")
    collection = product.get("collection", "luxury")  # noqa: F841
    price = _price_display(product, market)
    verified = product.get("authenticity_verified", False)
    condition = product.get("condition", "used")
    luxury = _is_luxury(product)

    # ── Hooks ────────────────────────────────────────────────────────────────
    if luxury:
        hooks = [
            VideoHook(
                type="shock",
                text=f"We got a {title} for {price}. Here's the full authenticity check. 🔍",
                duration_s=3,
            ),
            VideoHook(
                type="question",
                text=f"Can you spot a fake {brand}? Watch before you buy. ⚠️",
                duration_s=3,
            ),
            VideoHook(
                type="story",
                text=f"Our buyer flew to {('London' if market.lower() == 'uk' else 'Tokyo')} and found THIS {brand}…",
                duration_s=4,
            ),
            VideoHook(
                type="challenge",
                text=f"Name the retail price of this {brand} {category}. We sold it for {price} 👇",
                duration_s=3,
            ),
        ]
    else:
        hooks = [
            VideoHook(
                type="shock",
                text=f"We got {title} for ONLY {price}! How?! 🔥",
                duration_s=3,
            ),
            VideoHook(
                type="question",
                text=f"Is this the most underrated {brand} drop of the year? 👀",
                duration_s=3,
            ),
            VideoHook(
                type="challenge",
                text=f"Guess the retail on these {brand}s. Drop your answer below 👇",
                duration_s=3,
            ),
            VideoHook(
                type="story",
                text=f"How our buyer sourced 10 pairs of {brand} in 24 hours ⏱️",
                duration_s=4,
            ),
        ]

    # ── Caption ──────────────────────────────────────────────────────────────
    auth_line = "✅ 100% authenticated — certificate included." if verified else "📋 Condition report available on request."
    cta_map = {
        "hk": "💬 DM us or tap the link in bio to secure yours NOW 🔗",
        "uk": "💬 DM or click the link in bio — ships across the UK 🚚",
    }
    if luxury:
        headline = f"✨ {title} — {price}"
        body = (
            f"Condition: {condition.capitalize()} | Brand: {brand}\n"
            f"{auth_line}\n"
            f"Every piece sourced directly by our buyers. One-of-a-kind finds at pre-owned prices."
        )
    else:
        headline = f"🔥 {title} — {price}"
        body = (
            f"Condition: {condition.capitalize()} | Brand: {brand}\n"
            f"Limited stock — once it's gone, it's gone.\n"
            f"{auth_line}"
        )
    caption = VideoCaption(
        headline=headline,
        body=body,
        cta=cta_map.get(market.lower(), cta_map["hk"]),
    )

    # ── Talking points ───────────────────────────────────────────────────────
    if luxury:
        talking_points = [
            f"Open with the {brand} logo and date code close-up",
            "Show the authenticity certificate / hologram sticker on camera",
            f"Compare to retail price — highlight the {price} value",
            "Demonstrate hardware quality: zips, clasps, stitching",
            "Show interior lining and serial number",
            "End with a 360-degree product spin",
        ]
    else:
        talking_points = [
            "Open with the box / packaging reveal",
            f"Show sole, tongue label and size tag on {brand}",
            "Flex the colourway in good natural light",
            "Compare to retail or resell market price",
            "Show condition of the shoe from all angles",
            "End with a on-foot try-on (if available)",
        ]

    # ── B-roll suggestions ────────────────────────────────────────────────────
    if luxury:
        b_roll = [
            "Slow-motion product unboxing with tissue paper",
            "Macro shot of logo hardware / stitching",
            "Authentication certificate in focus",
            "Lifestyle shot — product on marble / wood surface",
            "Mirror reflection of product being held",
        ]
    else:
        b_roll = [
            "Overhead flat-lay on clean white background",
            "Slow-motion shoe drop",
            "Sole/toe-box detail shot",
            "Worn on-foot lifestyle shot (street / studio)",
            "Side-by-side with retail box",
        ]

    pack = VideoPack(
        product_id=pid,
        product_title=title,
        market=market.lower(),
        hooks=hooks,
        caption=caption,
        hashtags=_hashtags_for(product, market),
        recommended_format=VIDEO_FORMATS[0],   # vertical_9x16 default
        recommended_duration=VIDEO_DURATIONS["medium"],
        talking_points=talking_points,
        b_roll_suggestions=b_roll,
        music_vibe=_music_vibe(product),
        posting_time_suggestion=_posting_time(market),
    )
    return pack.to_dict()


def build_live_script(
    products: list[dict[str, Any]],
    duration_mins: int = 60,
    market: str = "hk",
) -> dict[str, Any]:
    """
    Generate a TikTok Live streaming script.

    Args:
        products: List of product dicts (same format as generate_video_pack).
        duration_mins: Target total live duration in minutes (default 60).
        market: "hk" | "uk"

    Returns:
        LiveScript.to_dict()
    """
    if not MOCK_MODE:
        raise NotImplementedError(
            "Real TikTok Live API not yet wired."
        )

    m = market.lower()
    CURRENCY_SYMBOL.get(m, "HK$")  # noqa: F841

    # ── Intro ─────────────────────────────────────────────────────────────────
    if m == "uk":
        intro = textwrap.dedent(f"""
            🎉 Welcome everyone! You're live with BuyerOS — your trusted source
            for authenticated luxury and premium pre-owned finds in the UK.
            Smash that LIKE button if you can hear us! 👍
            Tonight we have {len(products)} incredible pieces lined up —
            each one sourced directly by our buyers, fully authenticated.
            Drop a 👋 in the comments so we know where you're watching from!
            Let's get started in 3… 2… 1…
        """).strip()
    else:
        intro = textwrap.dedent(f"""
            🎉 大家好！歡迎來到 BuyerOS 直播！
            今晚我哋有 {len(products)} 件精選好貨等住大家！
            每件都係我哋 buyer 親自搵返嚟，全部正品保證 ✅
            想睇邊樣先打個數字落 comment 度！
            準備好未？3… 2… 1… 開賣！🔥
        """).strip()

    # ── Product segments ──────────────────────────────────────────────────────
    usable_mins = duration_mins - LIVE_INTRO_MINS - LIVE_OUTRO_MINS
    seg_mins = max(3, usable_mins // max(len(products), 1))

    segments: list[LiveSegment] = []
    for i, product in enumerate(products, start=1):
        pid = product.get("id", f"prod_{i:03d}")
        title = product.get("title", f"Product {i}")
        price = _price_display(product, market)
        verified = product.get("authenticity_verified", False)
        _is_luxury(product)  # used in template logic, not directly referenced
        brand = product.get("brand", "")

        if m == "uk":
            intro_line = f"Okay, item number {i} — this is the one I've been excited about. {title}. Price: {price}."
            key_points = [
                f"Tell the story: how and where this {brand} was sourced",
                "Hold product up to camera — 360° spin",
                "Zoom in on logo / date code / serial number",
                "Read out authenticity status: " + ("✅ Fully authenticated" if verified else "📋 Condition report provided"),
                "Compare to retail / current resell market",
                "Answer any comments live",
            ]
            auth_pitch = (
                "Every item we sell comes with our BuyerOS authenticity guarantee. "
                "If it's not real, you get a full refund. No questions asked."
                if verified else
                "We've done a thorough condition report on this one — I'll share it in the comments now."
            )
            urgency_line = f"We only have ONE of these. Once it's gone from this screen, it's gone. {price} — who wants it?"
            cta_line = "Type MINE in the comments or click the cart icon now! 🛒"
        else:
            intro_line = f"好！第 {i} 件嚟喇！就係呢個 {title}！今晚售價 {price}！"
            key_points = [
                f"講吓 {brand} 嘅故事：點買返嚟",
                "拎起產品對住鏡頭轉一圈",
                "放大 logo / 日期碼 / 序列號",
                "正品狀態：" + ("✅ 已認證" if verified else "📋 有驗貨報告"),
                "同市場價格比較",
                "即時回答觀眾問題",
            ]
            auth_pitch = (
                "BuyerOS 每件貨都有正品保證。假一賠十，無條件退款。"
                if verified else
                "呢件有完整驗貨報告，我而家 comment 俾大家睇。"
            )
            urgency_line = f"只有一件！消失咗就無喇！{price}！"
            cta_line = "打「搶」落 comment！或者撳購物車！🛒"

        segments.append(LiveSegment(
            segment_no=i,
            product_id=pid,
            product_title=title,
            price_display=price,
            duration_mins=seg_mins,
            intro_line=intro_line,
            key_points=key_points,
            authenticity_pitch=auth_pitch,
            urgency_line=urgency_line,
            cta_line=cta_line,
        ))

    # ── Engagement prompts ────────────────────────────────────────────────────
    if m == "uk":
        engagement_prompts = [
            "Drop a 🔥 if you're loving what you see!",
            "Share this live with a friend who needs this in their life!",
            "Type YES if you want to see more luxury finds like this!",
            "We're going to do a giveaway at the end — stay tuned! 🎁",
            "Any questions on authenticity? Drop them below — we answer everything.",
        ]
        pinned_comment = (
            "✅ BuyerOS LIVE | Authenticated Luxury & Premium Pre-Owned\n"
            "🛒 Shop: [link in bio]\n"
            "📬 DM for sizing / condition reports\n"
            "🔒 Secure checkout | UK-wide shipping"
        )
        outro = textwrap.dedent("""
            That's it for tonight everyone! Thank you so much for joining us live —
            you're the best community in the world. 🙏
            All items we showed tonight are still available via the link in bio.
            Follow us so you never miss a drop, and we'll see you next time.
            Take care! 👋
        """).strip()
    else:
        engagement_prompts = [
            "覺得靚打個🔥！",
            "分享俾朋友，讓更多人睇到！",
            "想要更多名牌好貨打 YES！",
            "直播尾段有 giveaway！留守😍",
            "有任何問題打落 comment，我哋即刻答！",
        ]
        pinned_comment = (
            "✅ BuyerOS 直播 | 正品名牌二手\n"
            "🛒 購物：[bio link]\n"
            "📬 DM 問尺寸 / 驗貨報告\n"
            "🔒 安全付款 | 全港送貨"
        )
        outro = textwrap.dedent("""
            今晚到此為止！多謝大家嚟撐 BuyerOS！🙏
            今晚所有產品 bio 入面都仲有得買，手快有手慢冇！
            記得 follow 我哋，唔好錯過下次直播！
            下次見！👋
        """).strip()

    script = LiveScript(
        market=m,
        total_duration_mins=duration_mins,
        intro=intro,
        segments=segments,
        outro=outro,
        engagement_prompts=engagement_prompts,
        pinned_comment_suggestion=pinned_comment,
    )
    return script.to_dict()


def build_ads_brief(
    product: dict[str, Any],
    objective: str = "product_sales",
    budget_hkd: float = 3000.0,
    market: str = "hk",
) -> dict[str, Any]:
    """
    Generate a TikTok ads creative brief for a product.

    Args:
        product: Product dict (same format as generate_video_pack).
        objective: TikTok campaign objective. One of:
            traffic | conversion | product_sales |
            reach | video_views | lead_generation
        budget_hkd: Total campaign budget in HKD.
        market: "hk" | "uk"

    Returns:
        AdsBrief.to_dict()
    """
    if not MOCK_MODE:
        raise NotImplementedError(
            "Real TikTok Ads API not yet wired."
        )

    if objective not in ADS_OBJECTIVES:
        objective = "product_sales"

    pid = product.get("id", "unknown")
    title = product.get("title", "Unknown Product")
    brand = product.get("brand", "")
    category = product.get("category", "item")
    price = _price_display(product, market)
    verified = product.get("authenticity_verified", False)
    luxury = _is_luxury(product)
    m = market.lower()
    budget_gbp = round(budget_hkd * 0.098, 2)

    # ── Creative direction ────────────────────────────────────────────────────
    if luxury:
        creative_direction = (
            f"Lead with mystery and aspiration. Open on a close-up of the {brand} logo. "
            f"Slow-motion reveal of the full product. "
            f"Overlay the authenticity certificate on screen. "
            f"Contrast the retail price vs our {price} asking price. "
            f"Tone: calm, premium, trustworthy. "
            f"Avoid fast cuts — let the product breathe."
        )
    else:
        creative_direction = (
            f"Lead with energy and hype. Quick-cut unboxing reveal. "
            f"Show the {brand} branding clearly within first 2 seconds. "
            f"On-foot / worn content if available. "
            f"Price shock: flash our {price} price in big text. "
            f"Tone: energetic, street-credible, limited-drop urgency."
        )

    # ── Copy ─────────────────────────────────────────────────────────────────
    auth_suffix = " | Authenticated ✅" if verified else ""
    if m == "uk":
        primary_copy = f"{title}{auth_suffix} — {price}. Pre-owned luxury with BuyerOS guarantee."
        secondary_copy = (
            f"Shop authenticated {brand} at pre-owned prices. "
            f"Every piece sourced by our expert buyers. Limited stock — act fast."
        )
        cta_button = "Shop Now"
        landing_page = f"https://buyeros.com/uk/{category}s/{pid}"
    else:
        primary_copy = f"{title}{auth_suffix} — {price}。正品保證，限量出售。"
        secondary_copy = (
            f"BuyerOS 買手直接搵返嚟嘅 {brand}。"
            f"正品認證，一件都唔多。即刻搶購。"
        )
        cta_button = "立即購買"
        landing_page = f"https://buyeros.com/hk/{category}s/{pid}"

    # ── Dos and Don'ts ───────────────────────────────────────────────────────
    dos = [
        "Show the product within the first 3 seconds",
        "Include the price on screen in the first 5 seconds",
        "Use authentic lifestyle footage (no stock imagery)",
        "Feature the authenticity certificate / verification badge",
        "Add subtitles — 85% of TikTok is watched with sound off",
        "Test at least 3 creative variants (different hooks)",
    ]
    donts = [
        "Do NOT make unsubstantiated claims (e.g. '100% real' without evidence on screen)",
        "Do NOT use copyrighted music without TikTok Commercial Music Library clearance",
        "Do NOT show prices that differ from the live listing price",
        "Do NOT use misleading before/after comparisons",
        "Do NOT target under-18s for luxury goods",
        "Do NOT use the word 'fake' or 'replica' anywhere in copy or creative",
    ]

    brief = AdsBrief(
        product_id=pid,
        product_title=title,
        market=m,
        objective=objective,
        budget_hkd=budget_hkd,
        budget_gbp=budget_gbp,
        target_audience=_audience_for(product, market),
        creative_direction=creative_direction,
        primary_copy=primary_copy,
        secondary_copy=secondary_copy,
        cta_button=cta_button,
        landing_page_suggestion=landing_page,
        budget_split=_budget_split(budget_hkd, objective),
        kpi_targets=_kpi_targets(objective, budget_hkd),
        dos=dos,
        donts=donts,
    )
    return brief.to_dict()


# ---------------------------------------------------------------------------
# Status / health
# ---------------------------------------------------------------------------

def status() -> dict[str, Any]:
    """Return connector health status. Safe to expose via API."""
    return {
        "connector": "tiktok",
        "mock_mode": MOCK_MODE,
        "configured": not MOCK_MODE,
        "env_vars": {
            "TIKTOK_ACCESS_TOKEN": bool(TIKTOK_ACCESS_TOKEN),
            "TIKTOK_APP_ID": bool(TIKTOK_APP_ID),
        },
        "capabilities": [
            "generate_video_pack",
            "build_live_script",
            "build_ads_brief",
        ],
        "supported_markets": ["hk", "uk"],
        "supported_objectives": ADS_OBJECTIVES,
    }
