"""Regressions for CSS leaking past a Markdown raw-HTML block boundary."""

from html.parser import HTMLParser
from pathlib import Path

from streamlit.testing.v1 import AppTest

from agrinova.ui.theme import CSS

APP = Path(__file__).resolve().parents[2] / "app.py"


class StyleContent(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_style = False
        self.styles = []
        self.outside = []

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self.in_style = True

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        (self.styles if self.in_style else self.outside).append(data)


def test_entire_theme_is_one_markdown_raw_html_style_block():
    # CommonMark ends a style HTML block at the line containing </style>.
    # A concatenated </style><style> can leave subsequent lines as ordinary
    # Markdown. Require one wrapper around every base and override rule.
    assert CSS.count("<style>") == CSS.count("</style>") == 1
    assert CSS.startswith("<style>\n")
    assert CSS.rstrip().endswith("\n</style>")
    parsed = StyleContent()
    parsed.feed(CSS)
    assert not "".join(parsed.outside).strip()
    stylesheet = "".join(parsed.styles)
    # Rules from the start, middle and end must all survive the fix.
    for selector in (".stApp", ".st-key-dashboard_page", ".overview-hero",
                     "stMetric", "stPlotlyChart", ".comparison-summary", "@container"):
        assert selector in stylesheet


def test_app_emits_the_theme_as_html_enabled_markdown_not_visible_css_text():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    theme = [element for element in app.markdown if element.value == CSS]
    assert len(theme) == 1
    assert theme[0].proto.allow_html is True
    for element in app.markdown:
        if "<style>" not in element.value:
            continue
        assert element.proto.allow_html is True
        assert element.value.count("<style>") == element.value.count("</style>") == 1
        parsed = StyleContent()
        parsed.feed(element.value)
        assert not "".join(parsed.outside).strip()
    for kind in ("text", "code"):
        assert all(".overview-hero" not in element.value and ".comparison-summary" not in element.value
                   for element in app.get(kind))
