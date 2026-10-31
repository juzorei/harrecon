# harrecon

Turn a HAR capture into a private API's inventory, response schemas and a typed Python client — offline, stdlib only.

```text
$ harrecon inventory capture.har
captured 5 entries, 2 JSON endpoints

auth mechanisms:
  authorization: Bearer: [redacted] (32 chars)

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
     $.currency: added (string)

$ harrecon gen capture.har "GET /v1/lots/{id}" --out client.py
```

## Commands

```text
harrecon inventory <har> [--host H] [--json]     # endpoints + auth mechanisms (redacted)
harrecon schema <har> "<METHOD> /path" [--json]  # merged schema across samples, optional-fields aware
harrecon diff <har_a> <har_b> [--json] [--fail-on-change] # endpoints and field-level schema changes
harrecon gen <har> "<METHOD> /path" [--out f.py] # typed dataclass client skeleton (urllib, review before use)
```

Numeric path segments collapse to `{id}` so repeated calls count as one endpoint. Static assets, HTML and tracking noise are excluded. Auth samples are redacted in all output. Python 3.11+, stdlib only.

## Field-level diffs (0.2.0)

Nested fields use paths such as `$.items[].price`. Keys containing dots, quotes or spaces use bracket notation, e.g. `$["unit.price"]`. Changes report added/removed fields, changed types and optionality. Renames are not inferred.

`diff --json` retains `added`, `removed`, and full `before`/`after` schemas. Changed endpoints now also include `host` and `changes`: records containing `path`, `kind` (`field_added`, `field_removed`, `type_changed`, `optional_changed`), `before`, and `after`. Field additions/removals carry schema objects and null for the absent side; type changes carry strings; optionality changes carry booleans. `added_details` and `removed_details` provide endpoint/host objects without changing the original string arrays.

`--fail-on-change` returns 1 on any observed endpoint/schema difference, 0 on no difference, and 2 on input/usage errors. Default behavior remains report-only (exit 0). Compare equivalent flows: capture differences are not proof of an API breaking change. Values, HTTP status changes and authentication changes are outside this schema diff.

Inventory auth values now show only `[redacted]` and their length, never credential prefixes. The input HAR and generated client are not sanitized by this output masking.

Install: `pip install harrecon` — or from this repo:
`pip install "git+https://github.com/juzorei/harrecon#subdirectory=tools/harrecon"`

The companion agent skill lives in [skills/har-to-api-client](../skills/har-to-api-client): capture hygiene, auth identification, schema caveats (inference from samples ≠ documentation), diff-based scraper debugging, and the ToS boundaries. Skills: `npx skills add juzorei/harrecon`.
