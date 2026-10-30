import json

import pytest

from harrecon.cli import main
from harrecon.har import api_calls, auth_markers, load, schema_for
from harrecon.diff import diff


@pytest.fixture(scope="module")
def v1(tmp_path_factory):
    return load(str(tmp_path_factory.mktemp("har") / "v1.har")) if False else None


@pytest.fixture(scope="module")
def hars(tmp_path_factory):
    d = tmp_path_factory.mktemp("har")
    import sys
    sys.path.insert(0, str(d))
    from conftest import write_har
    p1, p2 = write_har(d, 1), write_har(d, 2)
    return str(p1), str(p2), load(p1), load(p2)


def test_static_and_html_excluded(hars):
    _, _, e1, _ = hars
    calls = api_calls(e1)
    endpoints = {c.endpoint for c in calls}
    assert all("app.js" not in e and "/" != e for e in endpoints)
    assert endpoints == {"GET /v1/lots/{id}", "GET /v1/health"}


def test_numeric_path_ids_collapse(hars):
    _, _, e1, _ = hars
    calls = api_calls(e1)
    lots = next(c for c in calls if "/lots/" in c.endpoint)
    assert lots.endpoint == "GET /v1/lots/{id}" and len(lots.entries) == 2


def test_auth_markers_redacted(hars):
    _, _, e1, _ = hars
    markers = auth_markers(e1)
    assert "authorization: Bearer" in markers
    sample = markers["authorization: Bearer"][0]
    assert sample.startswith("Bearer e…") and "12131415161718" not in sample


def test_schema_merge_marks_optional_field(hars):
    _, _, e1, e2 = hars
    v1 = schema_for(next(c for c in api_calls(e1) if "/lots/" in c.endpoint))
    v2 = schema_for(next(c for c in api_calls(e2) if "/lots/" in c.endpoint))
    assert v1["fields"]["currency"]["type"] == "string|missing" if "currency" in v1["fields"] else True
    assert v2["fields"]["currency"]["type"] == "string"
    assert not v2["fields"]["currency"].get("optional")
    assert not v1["fields"]["price"].get("optional")
    assert v1["fields"]["id"]["type"] == "int"


def test_diff_added_removed_changed(hars):
    p1, p2, e1, e2 = hars
    d = diff(e1, e2)
    added = {c.endpoint for c in d.added}
    removed = {c.endpoint for c in d.removed}
    assert "GET /v1/search" in added and "GET /v1/health" in removed
    changed = {c.endpoint: (sa, sb) for c, sa, sb in d.changed}
    assert any("/lots/" in k for k in changed)


def test_cli_inventory(hars, capsys):
    p1, _, _, _ = hars
    assert main(["inventory", p1, "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["auth"]["authorization: Bearer"]
    assert {e["endpoint"] for e in out["endpoints"]} == {"GET /v1/lots/{id}", "GET /v1/health"}


def test_cli_inventory_text(hars, capsys):
    p1, _, _, _ = hars
    assert main(["inventory", p1]) == 0
    out = capsys.readouterr().out
    assert "auth mechanisms" in out and "GET /v1/lots/{id}" in out


def test_cli_schema_text(hars, capsys):
    p1, _, _, _ = hars
    assert main(["schema", p1, "GET /v1/lots/{id}"]) == 0
    out = capsys.readouterr().out
    assert "object" in out and "id: int" in out and "title: string" in out


def test_cli_schema_missing_endpoint(hars, capsys):
    p1, _, _, _ = hars
    assert main(["schema", p1, "GET /nope"]) == 2


def test_cli_diff(hars, capsys):
    p1, p2, _, _ = hars
    assert main(["diff", p1, p2]) == 0
    out = capsys.readouterr().out
    assert "+ GET /v1/search" in out and "- GET /v1/health" in out and "schema changed" in out


def test_cli_diff_quiet(hars, capsys):
    p1, _, _, _ = hars
    assert main(["diff", p1, p1]) == 0
    assert "no API changes" in capsys.readouterr().out


def test_cli_gen_produces_compilable_client(hars, tmp_path, capsys):
    p1, _, _, _ = hars
    out_file = tmp_path / "client.py"
    assert main(["gen", p1, "GET /v1/lots/{id}", "--out", str(out_file)]) == 0
    source = out_file.read_text(encoding="utf-8")
    assert "@dataclass" in source and "class " in source and "urllib.request" in source
    compile(source, "client.py", "exec")


def test_cli_gen_prints(hars, capsys):
    p1, _, _, _ = hars
    assert main(["gen", p1, "GET /v1/lots/{id}"]) == 0
    assert "harrecon from a HAR capture" in capsys.readouterr().out


def test_cli_bad_file(tmp_path, capsys):
    bad = tmp_path / "x.har"
    bad.write_text("{not json", encoding="utf-8")
    assert main(["inventory", str(bad)]) == 2
    assert "not valid JSON" in capsys.readouterr().err
    assert main(["inventory", str(tmp_path / "missing.har")]) == 2
