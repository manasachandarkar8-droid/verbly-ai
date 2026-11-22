from app.services.seo.analysis import (
    analyze_canonical,
    analyze_headings,
    analyze_images,
    analyze_keyword_relationships,
    analyze_links,
    analyze_meta_description,
    analyze_open_graph,
    analyze_robots,
    analyze_title,
    analyze_url,
)
from app.services.seo.constants import META_DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH
from app.services.seo.html_parser import HeadingTag, ImageTag, LinkTag
from app.services.seo.keywords import KeywordStat

# --- Title -----------------------------------------------------------------


def test_title_missing():
    result = analyze_title([])
    assert result.present is False
    assert result.length_status == "missing"
    assert result.issues


def test_title_present_but_empty():
    result = analyze_title([""])
    assert result.present is False
    assert result.length_status == "missing"


def test_title_too_short():
    result = analyze_title(["Short"])
    assert result.length_status == "too_short"
    assert result.issues


def test_title_too_long():
    result = analyze_title(["x" * (TITLE_MAX_LENGTH + 20)])
    assert result.length_status == "too_long"
    assert result.issues


def test_title_valid_length():
    result = analyze_title(["A Perfectly Reasonable Page Title For SEO"])
    assert result.length_status == "good"
    assert result.issues == []


def test_title_duplicate_tags():
    result = analyze_title(["A Perfectly Reasonable Page Title For SEO", "Second Title"])
    assert result.duplicate_tags_found is True
    assert any("duplicate" not in i.lower() and "tags" in i.lower() or "Found 2" in i for i in result.issues)


# --- Meta description --------------------------------------------------


def test_meta_description_missing():
    result = analyze_meta_description([])
    assert result.present is False
    assert result.length_status == "missing"


def test_meta_description_short():
    result = analyze_meta_description(["Too short."])
    assert result.length_status == "too_short"


def test_meta_description_long():
    result = analyze_meta_description(["x" * (META_DESCRIPTION_MAX_LENGTH + 30)])
    assert result.length_status == "too_long"


def test_meta_description_valid():
    result = analyze_meta_description(["x" * 140])
    assert result.length_status == "good"
    assert result.issues == []


def test_meta_description_duplicate():
    result = analyze_meta_description(["x" * 140, "y" * 140])
    assert result.duplicate_tags_found is True


# --- Headings ----------------------------------------------------------


def test_headings_no_h1():
    result = analyze_headings([HeadingTag(level=2, text="Sub")])
    assert result.h1_count == 0
    assert any("No <h1>" in i for i in result.issues)


def test_headings_single_h1():
    result = analyze_headings([HeadingTag(level=1, text="Main")])
    assert result.h1_count == 1
    assert result.has_multiple_h1 is False
    assert not any("h1" in i.lower() and "found" in i.lower() and "1 <h1>" not in i for i in result.issues)


def test_headings_multiple_h1():
    result = analyze_headings([HeadingTag(level=1, text="A"), HeadingTag(level=1, text="B")])
    assert result.has_multiple_h1 is True
    assert any("Found 2" in i for i in result.issues)


def test_headings_valid_hierarchy_h2_to_h3_to_h4():
    headings = [
        HeadingTag(level=1, text="Title"),
        HeadingTag(level=2, text="Section"),
        HeadingTag(level=3, text="Sub"),
        HeadingTag(level=4, text="Detail"),
    ]
    result = analyze_headings(headings)
    assert result.hierarchy_gaps_found is False


def test_headings_hierarchy_skip_detected():
    headings = [
        HeadingTag(level=1, text="Title"),
        HeadingTag(level=2, text="Section"),
        HeadingTag(level=4, text="Jumped past H3"),
    ]
    result = analyze_headings(headings)
    assert result.hierarchy_gaps_found is True


def test_headings_going_back_up_is_not_a_skip():
    # H1 -> H2 -> H3 -> H2 again is normal document structure, not a skip.
    headings = [
        HeadingTag(level=1, text="Title"),
        HeadingTag(level=2, text="Section A"),
        HeadingTag(level=3, text="Sub"),
        HeadingTag(level=2, text="Section B"),
    ]
    result = analyze_headings(headings)
    assert result.hierarchy_gaps_found is False


def test_headings_counts_by_level():
    headings = [HeadingTag(level=2, text="A"), HeadingTag(level=2, text="B"), HeadingTag(level=3, text="C")]
    result = analyze_headings(headings)
    assert result.counts_by_level == {"h1": 0, "h2": 2, "h3": 1, "h4": 0, "h5": 0, "h6": 0}
    assert result.total == 3


# --- URL -------------------------------------------------------------------


def test_url_https():
    result = analyze_url("https://example.com/page")
    assert result.is_https is True
    assert not any("HTTPS" in i for i in result.issues)


def test_url_http_flagged():
    result = analyze_url("http://example.com/page")
    assert result.is_https is False
    assert any("HTTPS" in i for i in result.issues)


def test_url_with_ordinary_query_param_not_flagged_as_bad():
    result = analyze_url("https://example.com/search?id=42")
    assert result.has_query_parameters is True
    assert result.tracking_parameters_found == []


def test_url_with_tracking_param_flagged():
    result = analyze_url("https://example.com/page?utm_source=newsletter&id=5")
    assert "utm_source" in result.tracking_parameters_found
    assert any("tracking" in i.lower() for i in result.issues)


def test_url_length_long():
    long_path = "a" * 200
    result = analyze_url(f"https://example.com/{long_path}")
    assert result.length_status == "long"


def test_url_fragment_detected():
    result = analyze_url("https://example.com/page#section")
    assert result.has_fragment is True


# --- Images ------------------------------------------------------------


def test_images_none_found():
    result = analyze_images([])
    assert result.total == 0
    assert result.alt_text_coverage_percent == 0.0
    assert result.issues == []


def test_images_all_have_alt_text():
    images = [ImageTag(src="a.jpg", alt_present=True, alt_value="cat")]
    result = analyze_images(images)
    assert result.alt_text_coverage_percent == 100.0
    assert result.without_alt_text == 0


def test_images_missing_alt_attribute():
    images = [ImageTag(src="a.jpg", alt_present=False, alt_value="")]
    result = analyze_images(images)
    assert result.without_alt_text == 1
    assert result.issues


def test_images_empty_alt_tracked_separately():
    images = [ImageTag(src="a.jpg", alt_present=True, alt_value="")]
    result = analyze_images(images)
    assert result.empty_alt_count == 1
    assert result.with_alt_text == 0


def test_images_alt_coverage_percentage():
    images = [
        ImageTag(src="a.jpg", alt_present=True, alt_value="cat"),
        ImageTag(src="b.jpg", alt_present=False, alt_value=""),
    ]
    result = analyze_images(images)
    assert result.alt_text_coverage_percent == 50.0


# --- Links ---------------------------------------------------------------


def test_links_internal_and_external_classification():
    links = [
        LinkTag(href="/about"),
        LinkTag(href="https://example.com/contact"),
        LinkTag(href="https://external-site.com/page"),
    ]
    result = analyze_links(links, page_url="https://example.com/home")
    assert result.internal == 2
    assert result.external == 1


def test_links_without_usable_href():
    links = [LinkTag(href="#"), LinkTag(href="javascript:void(0)"), LinkTag(href="mailto:a@b.com")]
    result = analyze_links(links, page_url="https://example.com/")
    assert result.without_usable_href == 3
    assert result.internal == 0 and result.external == 0


def test_links_no_links():
    result = analyze_links([], page_url="https://example.com/")
    assert result.total == 0


# --- Canonical ---------------------------------------------------------


def test_canonical_missing():
    result = analyze_canonical([], page_url="https://example.com/")
    assert result.present is False
    assert result.matches_page_url is None


def test_canonical_present_matches():
    result = analyze_canonical(["https://example.com/page"], page_url="https://example.com/page")
    assert result.matches_page_url is True
    assert result.issues == []


def test_canonical_present_but_differs():
    result = analyze_canonical(["https://example.com/other"], page_url="https://example.com/page")
    assert result.matches_page_url is False
    assert result.issues


def test_canonical_duplicate():
    result = analyze_canonical(
        ["https://example.com/a", "https://example.com/b"], page_url="https://example.com/a"
    )
    assert result.duplicate_tags_found is True


# --- Robots ------------------------------------------------------------


def test_robots_missing():
    result = analyze_robots([])
    assert result.present is False
    assert result.indexing_allowed is None


def test_robots_noindex():
    result = analyze_robots(["noindex"])
    assert result.indexing_allowed is False
    assert result.following_allowed is True


def test_robots_nofollow():
    result = analyze_robots(["nofollow"])
    assert result.following_allowed is False
    assert result.indexing_allowed is True


def test_robots_index_follow_explicit():
    result = analyze_robots(["index, follow"])
    assert result.indexing_allowed is True
    assert result.following_allowed is True


def test_robots_case_insensitive():
    result = analyze_robots(["NOINDEX, NOFOLLOW"])
    assert result.indexing_allowed is False
    assert result.following_allowed is False


# --- Open Graph --------------------------------------------------------


def test_open_graph_all_present():
    tags = {
        "og:title": ["Title"],
        "og:description": ["Desc"],
        "og:type": ["article"],
        "og:url": ["https://example.com/"],
        "og:image": ["https://example.com/i.png"],
    }
    result = analyze_open_graph(tags)
    assert result.missing_tags == []
    assert result.title == "Title"


def test_open_graph_all_missing():
    result = analyze_open_graph({})
    assert set(result.missing_tags) == {"og:title", "og:description", "og:type", "og:url", "og:image"}
    assert result.issues


def test_open_graph_duplicate_detected():
    tags = {"og:title": ["First", "Second"]}
    result = analyze_open_graph(tags)
    assert "og:title" in result.duplicate_tags_found


# --- Keyword relationships -----------------------------------------------


def test_keyword_relationships_presence():
    keywords = [KeywordStat(keyword="python", count=3, density=50.0)]
    relationships = analyze_keyword_relationships(
        keywords,
        title="Learn Python Fast",
        meta_description="A guide to programming.",
        body_text="python python python code",
    )
    assert relationships[0].in_title is True
    assert relationships[0].in_meta_description is False
    assert relationships[0].in_content is True


def test_keyword_relationships_handles_missing_title_and_description():
    keywords = [KeywordStat(keyword="python", count=1, density=100.0)]
    relationships = analyze_keyword_relationships(
        keywords, title=None, meta_description=None, body_text="python"
    )
    assert relationships[0].in_title is False
    assert relationships[0].in_meta_description is False


def test_keyword_relationships_empty_keywords_list():
    assert analyze_keyword_relationships([], title="x", meta_description="y", body_text="z") == []
