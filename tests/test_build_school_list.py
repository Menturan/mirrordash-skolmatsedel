# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path

import pytest

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


def test_the_crawl_never_starts_without_a_yes(monkeypatch, capsys):
    monkeypatch.setattr(bsl, "crawl", lambda failed: pytest.fail("the crawl must not start"))
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    assert bsl.main([]) == 1
    assert "Nothing changed" in capsys.readouterr().err


def test_a_crawl_with_failed_pages_leaves_the_old_list_alone(monkeypatch, tmp_path):
    def broken_crawl(failed):
        failed.append("/d/somewhere")
        return []
    monkeypatch.setattr(bsl, "crawl", broken_crawl)
    monkeypatch.setattr(bsl, "OUTPUT", tmp_path / "schools.json")
    assert bsl.main(["--yes"]) == 1
    assert not (tmp_path / "schools.json").exists()


def test_a_good_crawl_writes_the_list(monkeypatch, tmp_path):
    provinces = [{"slug": "p", "name": "P", "districts": [{"slug": "d", "name": "D", "schools": [{"slug": "s", "name": "S"}]}]}]
    monkeypatch.setattr(bsl, "crawl", lambda failed: provinces)
    monkeypatch.setattr(bsl, "OUTPUT", tmp_path / "schools.json")
    assert bsl.main(["--yes"]) == 0
    assert '"slug": "s"' in (tmp_path / "schools.json").read_text()
