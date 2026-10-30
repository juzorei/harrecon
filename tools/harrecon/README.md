# harrecon

Turn a HAR capture into a private API's inventory, response schemas and a typed Python client — offline, stdlib only.

```text
$ harrecon inventory capture.har
captured 6 entries, 2 JSON endpoints

auth mechanisms:
  authorization: Bearer: Bearer e…(32 chars)

  GET /v1/health   [api.example.com] 200
  GET /v1/lots/{id}  [api.example.com] 200/200

$ harrecon schema capture.har "GET /v1/lots/{id}"
object
  id: int
  title: string
  price: number

$ harrecon diff worked.har broken.har
  + GET /v1/search  [api.example.com]
  ~ GET /v1/lots/{id}  [api.example.com] schema changed:
     after: {"fields": {..., "currency": {"type": "string"}}}

$ harrecon gen capture.har "GET /v1/lots/{id}" --out client.py
```

## Commands

```text
harrecon inventory <har> [--host H] [--json]     # endpoints + auth mechanisms (redacted)
harrecon schema <har> "<METHOD> /path" [--json]  # merged schema across samples, optional-fields aware
harrecon diff <har_a> <har_b> [--json]           # added / removed / schema-changed — "did they change the API"
harrecon gen <har> "<METHOD> /path" [--out f.py] # typed dataclass client skeleton (urllib, review before use)
```

Numeric path segments collapse to `{id}` so repeated calls count as one endpoint. Static assets, HTML and tracking noise are excluded. Auth samples are redacted in all output. Python 3.11+, stdlib only.

Install: `pip install harrecon` — or from this repo:
`pip install "git+https://github.com/juzorei/harrecon#subdirectory=tools/harrecon"`

The companion agent skill lives in [skills/har-to-api-client](../skills/har-to-api-client): capture hygiene, auth identification, schema caveats (inference from samples ≠ documentation), diff-based scraper debugging, and the ToS boundaries. Skills: `npx skills add juzorei/harrecon`.
