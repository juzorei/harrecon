import json

import pytest

from harrecon.cli import main
from harrecon.har import api_calls, load, schema_for


def capture(tmp_path, name, bodies, host="api.example.com"):
    path = tmp_path / name
    path.write_text(json.dumps({"log": {"entries": [
        {"request": {"method": "GET", "url": f"https://{host}/v1/items/7"},
         "response": {"status": 200, "content": {
             "mimeType": "application/json", "text": json.dumps(body)}}}
        for body in bodies
    ]}}), encoding="utf-8")
    return str(path)


def test_diff_text_reports_nested_paths_without_truncation(tmp_path, capsys):
    common = {f"f{i}": i for i in range(40)}
    before = capture(tmp_path, "before.har", [{**common, "rows": [{"price": 7, "old": True}]}])
    after = capture(tmp_path, "after.har", [{**common, "rows": [{"price": "7", "new": 1}]}])
    assert main(["diff", before, after]) == 0
    output = capsys.readouterr().out
    assert "$.rows[].price: int -> string" in output
    assert "$.rows[].old: removed" in output
    assert "$.rows[].new: added" in output
    assert "api.example.com" in output


def test_diff_json_has_host_and_escaped_paths(tmp_path, capsys):
    before = capture(tmp_path, "before.har", [{"a.b": {"price": 7}}])
    after = capture(tmp_path, "after.har", [{"a.b": {"price": "7"}}])
    assert main(["diff", before, after, "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    changed = result["changed"][0]
    assert changed["host"] == "api.example.com"
    assert changed["before"]["type"] == changed["after"]["type"] == "object"
    assert changed["changes"] == [{"path": '$["a.b"].price', "kind": "type_changed",
                                   "before": "int", "after": "string"}]


@pytest.mark.parametrize("as_json", [False, True])
def test_fail_on_change_and_unchanged_exit_codes(tmp_path, capsys, as_json):
    before = capture(tmp_path, "before.har", [{"price": 7}])
    after = capture(tmp_path, "after.har", [{"price": "7"}])
    flags = ["--fail-on-change"] + (["--json"] if as_json else [])
    assert main(["diff", before, after, *flags]) == 1
    assert main(["diff", before, before, *flags]) == 0
    assert main(["diff", before, str(tmp_path / "missing.har"), *flags]) == 2


def test_endpoint_changes_are_host_qualified_and_fail_gate(tmp_path, capsys):
    before = capture(tmp_path, "before.har", [{}], host="old.example.com")
    after = capture(tmp_path, "after.har", [{}], host="new.example.com")
    assert main(["diff", before, after, "--json", "--fail-on-change"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["added"] == result["removed"] == ["GET /v1/items/{id}"]
    assert result["added_details"] == [{"endpoint": "GET /v1/items/{id}", "host": "new.example.com"}]
    assert result["removed_details"] == [{"endpoint": "GET /v1/items/{id}", "host": "old.example.com"}]


def test_optional_nested_field_survives_later_samples(tmp_path, capsys):
    before = capture(tmp_path, "before.har", [{"meta": {"id": 1}}])
    after = capture(tmp_path, "after.har", [
        {"meta": {"id": 1}}, {}, {"meta": {"id": 2}},
    ])
    schema = schema_for(api_calls(load(after))[0])
    assert schema["fields"]["meta"]["optional"] is True
    assert main(["diff", before, after, "--json"]) == 0
    change = json.loads(capsys.readouterr().out)["changed"][0]["changes"]
    assert change == [{"path": "$.meta", "kind": "optional_changed", "before": False, "after": True}]


def test_renamed_field_is_added_and_removed_not_guessed(tmp_path, capsys):
    before = capture(tmp_path, "before.har", [{"old_name": 1}])
    after = capture(tmp_path, "after.har", [{"new_name": 1}])
    assert main(["diff", before, after, "--json"]) == 0
    changes = json.loads(capsys.readouterr().out)["changed"][0]["changes"]
    assert {(c["path"], c["kind"]) for c in changes} == {
        ("$.old_name", "field_removed"), ("$.new_name", "field_added")}


def test_required_field_and_array_item_type_changes(tmp_path, capsys):
    before = capture(tmp_path, "before.har", [{"values": [1]}, {}])
    after = capture(tmp_path, "after.har", [{"values": ["one"]}])
    assert main(["diff", before, after, "--json"]) == 0
    changes = json.loads(capsys.readouterr().out)["changed"][0]["changes"]
    assert changes == [
        {"path": "$.values", "kind": "optional_changed", "before": True, "after": False},
        {"path": "$.values[]", "kind": "type_changed", "before": "int", "after": "string"},
    ]
