import json

import pytest

from harrecon.cli import main


@pytest.mark.parametrize("header,value", [
    ("Authorization", "Bearer tiny123"),
    ("Authorization", "Basic abc123"),
    ("Authorization", "bareSecret"),
    ("Authorization", "unknownSecret anotherSecret"),
    ("X-Api-Key", "tiny123"),
    ("X-Auth-Token", "long-secret-that-must-not-leak"),
    ("X-Csrf-Token", "csrfSecret"),
    ("X-Xsrf-Token", "xsrfSecret"),
    ("Cookie", "session=tiny123; private=anotherSecret"),
])
@pytest.mark.parametrize("as_json", [False, True])
def test_inventory_never_prints_credential_material(tmp_path, capsys, header, value, as_json):
    path = tmp_path / "auth.har"
    path.write_text(json.dumps({"log": {"entries": [{
        "request": {"method": "GET", "url": "https://example.com/data",
                    "headers": [{"name": header, "value": value}]},
        "response": {"status": 200, "content": {"mimeType": "application/json", "text": "{}"}},
    }]}}), encoding="utf-8")
    assert main(["inventory", str(path), *(["--json"] if as_json else [])]) == 0
    output = capsys.readouterr().out
    assert value not in output
    assert all(secret not in output for secret in [
        "tiny123", "abc123", "bareSecret", "unknownSecret", "anotherSecret", "long-sec",
        "csrfSecret", "xsrfSecret",
    ])
    assert "[redacted]" in output
