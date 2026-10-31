"""HAR parsing and API extraction: captures in, a private API's shape out."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

STATIC_EXT = re.compile(
    r"\.(js|css|png|jpe?g|gif|svg|woff2?|ttf|eot|ico|map|mp4|webm|webp|avif)(\?|$)", re.I)
JSON_TYPES = ("application/json", "application/problem+json", "application/vnd.api+json",
              "text/json")


@dataclass
class Entry:
    method: str
    scheme: str
    host: str
    path: str
    query: str
    status: int
    request_headers: dict[str, str]
    response_headers: dict[str, str]
    request_body: str | None
    response_body: str | None
    mime: str
    started: str

    @property
    def endpoint(self) -> str:
        return f"{self.method} {self.path}"

    @property
    def is_json(self) -> bool:
        return any(t in self.mime for t in JSON_TYPES)

    @property
    def is_static(self) -> bool:
        return bool(STATIC_EXT.search(self.path)) or "text/html" in self.mime


@dataclass
class ApiCall:
    entries: list[Entry] = field(default_factory=list)   # same endpoint, possibly multiple samples

    @property
    def endpoint(self) -> str:
        return self.entries[0].endpoint

    @property
    def host(self) -> str:
        return self.entries[0].host


def load(har_path: str) -> list[Entry]:
    data = json.loads(Path(har_path).read_text(encoding="utf-8", errors="replace"))
    entries = data.get("log", {}).get("entries", [])
    out = []
    for e in entries:
        req, resp = e.get("request", {}), e.get("response", {})
        url = req.get("url", "")
        parts = urlsplit(url)
        headers = {h.get("name", "").lower(): h.get("value", "") for h in req.get("headers", [])}
        resp_headers = {h.get("name", "").lower(): h.get("value", "") for h in resp.get("headers", [])}
        content = resp.get("content", {})
        body = content.get("text")
        post = req.get("postData", {})
        out.append(Entry(
            method=req.get("method", "GET").upper(),
            scheme=parts.scheme,
            host=parts.netloc,
            path=parts.path or "/",
            query=parts.query,
            status=int(resp.get("status", 0)),
            request_headers=headers,
            response_headers=resp_headers,
            request_body=post.get("text"),
            response_body=body,
            mime=(content.get("mimeType") or resp_headers.get("content-type", "")).split(";")[0],
            started=e.get("startedDateTime", ""),
        ))
    return out


def api_calls(entries: list[Entry], host: str | None = None) -> list[ApiCall]:
    """JSON API calls, static assets and html excluded. Numeric path ids collapse
    to {id} so /api/lots/123 and /api/lots/456 count as one endpoint."""
    import dataclasses

    calls: dict[tuple[str, str, str], ApiCall] = {}
    for e in entries:
        if host and e.host != host:
            continue
        if e.is_static or not e.is_json or e.status == 0:
            continue
        path = re.sub(r"/\d+(?=/|$)", "/{id}", e.path)
        key = (e.method, e.host, path)
        if key not in calls:
            calls[key] = ApiCall()
        calls[key].entries.append(dataclasses.replace(e, path=path))
    return sorted(calls.values(), key=lambda c: (c.host, c.endpoint))


def auth_markers(entries: list[Entry]) -> dict[str, list[str]]:
    """Which auth mechanisms the captured API actually uses, with redacted samples."""
    found: dict[str, list[str]] = {}
    def add(kind, value):
        red = f"[redacted] ({len(value)} chars)"
        found.setdefault(kind, [])
        if red not in found[kind]:
            found[kind].append(red)
    for e in entries:
        if not e.is_json:
            continue
        for h, v in e.request_headers.items():
            if h == "authorization":
                candidate, separator, _ = v.partition(" ")
                known = {"bearer": "Bearer", "basic": "Basic", "digest": "Digest",
                         "negotiate": "Negotiate", "token": "Token", "oauth": "OAuth",
                         "aws4-hmac-sha256": "AWS4-HMAC-SHA256"}
                scheme = known.get(candidate.lower(), "other") if separator else "other"
                add(f"authorization: {scheme}", v)
            elif h in ("x-api-key", "x-auth-token", "x-csrf-token", "x-xsrf-token"):
                add(f"header: {h}", v)
            elif h == "cookie" and v:
                add("cookie session", v.split(";", 1)[0].strip())
    return found


def _infer(value, samples: int = 1) -> dict:
    if isinstance(value, dict):
        return {"type": "object", "fields": {k: _infer(v, samples) for k, v in value.items()}}
    if isinstance(value, list):
        merged = {"type": "array", "items": None}
        for item in value[:5]:
            item_schema = _infer(item, samples)
            merged["items"] = item_schema if merged["items"] is None else merge_schema(merged["items"], item_schema)
        if merged["items"] is None:
            merged["items"] = {"type": "unknown"}
        return merged
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, (int, float)):
        return {"type": "number" if isinstance(value, float) else "int"}
    if value is None:
        return {"type": "null"}
    return {"type": "string"}


def merge_schema(a: dict, b: dict) -> dict:
    """Merge two samples of the same shape; fields missing on either side become optional."""
    merged = _merge_schema(a, b)
    if a.get("optional") or b.get("optional"):
        merged = {**merged, "optional": True}
    return merged


def _merge_schema(a: dict, b: dict) -> dict:
    if a.get("type") != b.get("type"):
        return {"type": f"{a.get('type')}|{b.get('type')}"}
    if "fields" in a and "fields" in b:
        fields = {}
        for k in dict.fromkeys(list(a["fields"]) + list(b["fields"])):
            if k in a["fields"] and k in b["fields"]:
                fields[k] = merge_schema(a["fields"][k], b["fields"][k])
            else:
                inner = a["fields"].get(k) or b["fields"].get(k)
                fields[k] = {**inner, "optional": True}
        return {"type": "object", "fields": fields}
    if a.get("items") is not None and b.get("items") is not None:
        return {"type": "array", "items": merge_schema(a["items"], b["items"])}
    return a


def schema_for(call: ApiCall) -> dict:
    """Merged response schema across all samples of the endpoint."""
    schema = None
    for e in call.entries:
        if not e.response_body:
            continue
        try:
            payload = json.loads(e.response_body)
        except (json.JSONDecodeError, ValueError):
            continue
        s = _infer(payload)
        schema = s if schema is None else merge_schema(schema, s)
    return schema or {"type": "unknown"}


def schema_json(schema: dict, indent: int = 0) -> str:
    """Human-readable schema tree."""
    pad = "  " * indent
    t = schema.get("type", "?")
    opt = " (optional)" if schema.get("optional") else ""
    if t == "object":
        lines = [f"{pad}object{opt}"]
        for k, v in schema.get("fields", {}).items():
            inner = schema_json(v, indent + 1)
            first, _, rest = inner.partition("\n")
            lines.append(f"{pad}  {k}: {first.strip()}")
            if rest:
                lines.append(rest)
        return "\n".join(lines)
    if t == "array":
        inner = schema_json(schema.get("items", {"type": "unknown"}), indent + 1)
        first, _, rest = inner.partition("\n")
        lines = [f"{pad}array of {first.strip()}{opt}"]
        if rest:
            lines.append(rest)
        return "\n".join(lines)
    return f"{pad}{t}{opt}"
