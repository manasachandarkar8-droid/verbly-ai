from app.services.seo.html_parser import parse_seo_html


def test_parses_title():
    result = parse_seo_html("<html><head><title>My Page</title></head></html>")
    assert result.titles == ["My Page"]


def test_missing_title():
    result = parse_seo_html("<html><head></head><body>hi</body></html>")
    assert result.titles == []


def test_duplicate_title_tags():
    html = "<html><head><title>First</title><title>Second</title></head></html>"
    result = parse_seo_html(html)
    assert result.titles == ["First", "Second"]


def test_meta_description_present():
    html = '<meta name="description" content="A great page about cats.">'
    result = parse_seo_html(html)
    assert result.meta_descriptions == ["A great page about cats."]


def test_meta_description_case_insensitive_attribute_name():
    html = '<META NAME="Description" CONTENT="Case insensitive test">'
    result = parse_seo_html(html)
    assert result.meta_descriptions == ["Case insensitive test"]


def test_duplicate_meta_description():
    html = (
        '<meta name="description" content="First desc.">'
        '<meta name="description" content="Second desc.">'
    )
    result = parse_seo_html(html)
    assert result.meta_descriptions == ["First desc.", "Second desc."]


def test_headings_extracted_with_levels_and_text():
    html = "<h1>Main Title</h1><h2>Sub A</h2><h2>Sub B</h2><h3>Detail</h3>"
    result = parse_seo_html(html)
    assert [(h.level, h.text) for h in result.headings] == [
        (1, "Main Title"),
        (2, "Sub A"),
        (2, "Sub B"),
        (3, "Detail"),
    ]


def test_multiple_h1():
    html = "<h1>One</h1><h1>Two</h1>"
    result = parse_seo_html(html)
    assert sum(1 for h in result.headings if h.level == 1) == 2


def test_images_alt_text_variants():
    html = (
        '<img src="a.jpg" alt="A cat">'
        '<img src="b.jpg" alt="">'
        '<img src="c.jpg">'
    )
    result = parse_seo_html(html)
    assert len(result.images) == 3
    assert result.images[0].alt_present is True and result.images[0].alt_value == "A cat"
    assert result.images[1].alt_present is True and result.images[1].alt_value == ""
    assert result.images[2].alt_present is False


def test_links_extracted():
    html = '<a href="/about">About</a><a href="https://external.com">Ext</a>'
    result = parse_seo_html(html)
    assert [link.href for link in result.links] == ["/about", "https://external.com"]


def test_links_without_href_ignored():
    html = '<a name="anchor">No href</a>'
    result = parse_seo_html(html)
    assert result.links == []


def test_canonical_link_detected():
    html = '<link rel="canonical" href="https://example.com/page">'
    result = parse_seo_html(html)
    assert result.canonical_hrefs == ["https://example.com/page"]


def test_canonical_rel_case_insensitive_and_multi_token():
    html = '<link rel="Canonical Alternate" href="https://example.com/page">'
    result = parse_seo_html(html)
    assert result.canonical_hrefs == ["https://example.com/page"]


def test_duplicate_canonical_tags():
    html = (
        '<link rel="canonical" href="https://example.com/a">'
        '<link rel="canonical" href="https://example.com/b">'
    )
    result = parse_seo_html(html)
    assert result.canonical_hrefs == ["https://example.com/a", "https://example.com/b"]


def test_robots_meta_extracted():
    html = '<meta name="robots" content="noindex, nofollow">'
    result = parse_seo_html(html)
    assert result.meta_robots == ["noindex, nofollow"]


def test_robots_meta_case_insensitive_attribute():
    html = '<META NAME="ROBOTS" CONTENT="noindex">'
    result = parse_seo_html(html)
    assert result.meta_robots == ["noindex"]


def test_open_graph_tags_extracted():
    html = (
        '<meta property="og:title" content="Great Page">'
        '<meta property="og:description" content="Great description">'
        '<meta property="og:type" content="article">'
        '<meta property="og:url" content="https://example.com/">'
        '<meta property="og:image" content="https://example.com/img.png">'
    )
    result = parse_seo_html(html)
    assert result.og_tags["og:title"] == ["Great Page"]
    assert result.og_tags["og:image"] == ["https://example.com/img.png"]


def test_duplicate_open_graph_tags():
    html = (
        '<meta property="og:title" content="First">'
        '<meta property="og:title" content="Second">'
    )
    result = parse_seo_html(html)
    assert result.og_tags["og:title"] == ["First", "Second"]


def test_body_text_excludes_script_and_style():
    html = (
        "<body>"
        "<script>var x = 'should not appear';</script>"
        "<style>.a { color: red; }</style>"
        "<p>Visible content here.</p>"
        "</body>"
    )
    result = parse_seo_html(html)
    assert "should not appear" not in result.body_text
    assert "color: red" not in result.body_text
    assert "Visible content here." in result.body_text


def test_heading_text_included_in_body_text_for_keyword_purposes():
    html = "<h1>Important Heading</h1><p>Body paragraph.</p>"
    result = parse_seo_html(html)
    assert "Important Heading" in result.body_text
    assert "Body paragraph." in result.body_text


def test_empty_html_does_not_raise():
    result = parse_seo_html("")
    assert result.titles == []
    assert result.headings == []
    assert result.body_text == ""


def test_malformed_html_does_not_raise():
    html = "<html><head><title>Unclosed<body><p>Broken markup"
    result = parse_seo_html(html)
    # Should not crash; best-effort extraction.
    assert isinstance(result.body_text, str)
