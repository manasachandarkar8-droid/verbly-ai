"""
Deterministic SEO thresholds and reference data.

Every threshold here is a widely-cited *heuristic*, not a universal rule
enforced by any search engine. They are kept as named, documented
constants (rather than magic numbers scattered through the analysis code)
so they can be tuned or overridden per-deployment without touching logic,
and so every warning we emit can point at an explicit, inspectable rule.
"""
from __future__ import annotations

# --- Title -------------------------------------------------------------
# Google typically renders ~50-60 characters of a title in SERPs before
# truncating; titles much shorter than this under-use the space available
# for keywords/branding.
TITLE_MIN_LENGTH = 30
TITLE_MAX_LENGTH = 60

# --- Meta description ----------------------------------------------------
# Commonly-cited SERP snippet length before truncation.
META_DESCRIPTION_MIN_LENGTH = 70
META_DESCRIPTION_MAX_LENGTH = 160

# --- Keywords --------------------------------------------------------------
# Tokens shorter than this are treated as noise (articles, single letters)
# rather than meaningful keywords.
MIN_KEYWORD_LENGTH = 3
# Default cap on how many top keywords are returned; callers of the
# service can request fewer, never more, via SEORequest.max_keywords.
DEFAULT_MAX_KEYWORDS = 15
HARD_MAX_KEYWORDS = 50

# --- URL -------------------------------------------------------------------
# Commonly-cited practical limit before URLs are truncated in SERPs / are
# considered unwieldy to share. Not a hard technical limit (browsers/
# servers allow far longer URLs).
URL_RECOMMENDED_MAX_LENGTH = 115

# Query parameters that are near-universally used purely for tracking
# rather than addressing distinct content. Presence of these does NOT by
# itself make a URL "bad" for SEO (canonicalization can still work fine);
# it is reported as informational context, not a hard failure.
KNOWN_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "gclid",
        "fbclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "ref",
        "igshid",
    }
)

# --- Input safety limits ----------------------------------------------------
# Feature 1's fetcher already caps response size via settings.max_response_bytes.
# This caps how many keyword tokens we will ever process/rank in one request,
# independent of that byte limit, to keep keyword extraction's CPU/memory cost
# bounded even for extremely dense/repetitive text.
MAX_TOKENS_ANALYZED = 200_000

# Common English stopwords, deliberately conservative (favors keeping
# borderline words like "how"/"why" out of the *stopword* list so genuine
# long-tail query terms aren't discarded). Kept as a plain stdlib set --
# no external dependency.
STOPWORDS: frozenset[str] = frozenset(
    """
    a an the and or but if then else when while of at by for with about
    against between into through during before after above below to from
    up down in out on off over under again further once here there all
    any both each few more most other some such no nor not only own same
    so than too very s t can will just don should now is are was were be
    been being have has had having do does did doing i me my myself we
    our ours ourselves you your yours yourself yourselves he him his
    himself she her hers herself it its itself they them their theirs
    themselves what which who whom this that these those am as until
    because until while of at by for with without within
    """.split()
)
