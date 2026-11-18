# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / "scripts" / "build_school_list.py"
_spec = importlib.util.spec_from_file_location("build_school_list", _path)
bsl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsl)

SCHOOL_HTML = """
<a href="/"><span>Skolmaten</span></a>
<a href="/p/gavleborgs-lan">Gävleborgs län</a>
<a href="/login">Logga in</a>
<a href="/about/privacy">Privacy</a>
<a href="/zeta-skola"><span aria-hidden="true">ZE</span><span><span>Zeta skola</span></span>
<span aria-hidden="true">chevron_right</span></a>
<a href="/alborga-skola"><span aria-hidden="true">AL</span><span>Alborga  skola</span></a>
<a href="/alborga-skola">duplicate</a>
"""


def test_parse_schools_filters_and_sorts():
    schools = bsl.parse_schools(SCHOOL_HTML)
    assert schools == [{"slug": "alborga-skola", "name": "Alborga skola"},
                       {"slug": "zeta-skola", "name": "Zeta skola"}]


def test_parse_provinces():
    html = '<a href="/p/a-lan">A län</a><a href="/p/a-lan">A län</a><a href="/d/x">X</a><a href="/p/">bad</a>'
    assert bsl.parse_provinces(html) == [{"slug": "a-lan", "name": "A län"}]


def test_parse_districts_ignores_nested_paths():
    html = '<a href="/d/gavle-kommun">Gävle kommun</a><a href="/d/a/b">no</a>'
    assert bsl.parse_districts(html) == [{"slug": "gavle-kommun", "name": "Gävle kommun"}]


def test_sorting_ignores_case():
    html = '<a href="/d/b">bravo</a><a href="/d/a">Alpha</a>'
    assert [d["slug"] for d in bsl.parse_districts(html)] == ["a", "b"]
