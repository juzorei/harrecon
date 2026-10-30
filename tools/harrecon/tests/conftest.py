"""Realistic HAR fixture: a private JSON API captured twice (before and after a field change)."""

import json

def make_har(version: int) -> dict:
    def entry(method, url, status, resp_body, req_headers=None, mime="application/json", post=None):
        headers = [{"name": k, "value": v} for k, v in (req_headers or {}).items()]
        e = {
            "startedDateTime": "2026-10-29T12:00:00.000Z",
            "request": {"method": method, "url": url, "headers": headers,
                        "queryString": [], "cookies": [], "headersSize": -1, "bodySize": 0},
            "response": {"status": status, "statusText": "OK",
                         "headers": [{"name": "Content-Type", "value": mime + "; charset=utf-8"}],
                         "content": {"size": len(resp_body or ""), "mimeType": mime,
                                     "text": resp_body},
                         "headersSize": -1, "bodySize": len(resp_body or "")},
        }
        if post:
            e["request"]["postData"] = {"mimeType": "application/json", "text": post}
        return e

    lots_v = {"id": 7, "title": "Ancient Orb", "price": 12.5}
    if version == 2:
        lots_v = {"id": 7, "title": "Ancient Orb", "price": 12.5, "currency": "chaos"}
    return {"log": {"version": "1.2", "creator": {"name": "fixture"}, "entries": [
        # static noise: must be excluded
        entry("GET", "https://cdn.example.com/app.js", 200, "console.log(1)",
              mime="application/javascript"),
        entry("GET", "https://example.com/", 200, "<html></html>", mime="text/html"),
        # the API under study
        entry("GET", "https://api.example.com/v1/lots/7",
              200, json.dumps(lots_v),
              req_headers={"Authorization": "Bearer eyJhbGciOi.12131415161718",
                           "X-Request-Id": "abc"}),
        entry("GET", "https://api.example.com/v1/lots/9",
              200, json.dumps({"id": 9, "title": "Exalted Shard", "price": 40.0} if version == 1
                              else {"id": 9, "title": "Exalted Shard", "price": 40.0,
                                    "currency": "chaos"}),
              req_headers={"Authorization": "Bearer eyJhbGciOi.12131415161718"}),
        # v1 had a health endpoint; v2 removed it and added a search endpoint
        *([entry("GET", "https://api.example.com/v1/health", 200, json.dumps({"ok": True}))]
          if version == 1 else []),
        *([] if version == 1 else [
            entry("GET", "https://api.example.com/v1/search?q=orb",
                  200, json.dumps({"results": [{"id": 7}], "total": 1}),
                  req_headers={"Authorization": "Bearer eyJhbGciOi.12131415161718"})]),
    ]}}


def write_har(directory, version=1, name=None):
    path = directory / (name or f"capture-v{version}.har")
    path.write_text(json.dumps(make_har(version), indent=2), encoding="utf-8")
    return path
