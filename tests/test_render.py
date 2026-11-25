"""The template drawn for real (Jinja, as the mirror does), with the days the module hands it."""

import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from mirrordash_skolmatsedel import plugin

SWEDISH = {"title": "Skolmatsedel"}
DAYS = [
    {"label": "Idag", "sub": "Onsdag", "dimmed": False,
     "schools": [{"name": "Alva", "dishes": ["Fisk", "Soppa"]}, {"name": "Elis", "dishes": ["Bulle & sås"]}]},
    {"label": "Fredag", "sub": "", "dimmed": True, "schools": [{"name": "", "dishes": ["Pannkakor"]}]},
]


@pytest.fixture
def draw():
    env = Environment(loader=FileSystemLoader(Path(plugin.__file__).parent / "templates"),
                      autoescape=select_autoescape(["html"]))

    def draw_it(**values):
        values = {"days": DAYS, "error": None, "show_header": True, "heading": "", **values}
        return env.get_template("widget.html").render(translations=SWEDISH, **values)
    return draw_it


def test_each_day_has_a_header_and_each_dish_its_own_line(draw):
    html = draw()
    assert html.count('class="sm-day-header"') == 2
    assert html.count('class="sm-dish"') == 4
    assert '<span class="sm-day-label">Idag</span>' in html and '<span class="sm-day-sub">Onsdag</span>' in html


def test_a_day_without_a_sub_label_has_none(draw):
    assert html_count(draw(), "sm-day-sub") == 1


def html_count(html: str, css_class: str) -> int:
    return html.count(f'class="{css_class}"')


def test_school_names_show_when_given_and_not_when_empty(draw):
    html = draw()
    assert '<div class="sm-school">Alva</div>' in html and '<div class="sm-school">Elis</div>' in html
    assert html_count(html, "sm-school") == 2  # the nameless row has no label


def test_the_dimmed_day_is_marked_and_the_other_is_not(draw):
    html = draw()
    assert html.count("sm-group is-dimmed") == 1 and html.count('class="sm-group"') == 1


def test_the_header_can_be_hidden(draw):
    assert "module-header" in draw() and "Skolmatsedel" in draw()
    assert "module-header" not in draw(show_header=False)


def test_dish_text_is_escaped(draw):
    assert "Bulle &amp; sås" in draw()


def test_an_error_shows_a_message_and_no_days(draw):
    html = draw(days=[], error="Kunde inte läsa")
    assert "module-message" in html and "Kunde inte läsa" in html and 'class="sm-day-header"' not in html


def test_the_template_uses_the_core_variables_not_copied_colors():
    source = (Path(plugin.__file__).parent / "templates" / "widget.html").read_text()
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", source.split("<style>")[1])  # no copied color values
    assert "var(--color-high-contrast)" in source and "var(--color-dimmed-charcoal)" in source
    assert "background" not in source.split("<style>")[1]  # no own background on the card


def test_heading_text_replaces_the_title(draw):
    assert "<h2 class=\"module-header\">Barnens lunch</h2>" in draw(heading="Barnens lunch")
