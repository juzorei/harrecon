# harrecon

[English](README.md) | [Русский](README.ru.md)

[![CI](https://github.com/juzorei/harrecon/actions/workflows/ci.yml/badge.svg)](https://github.com/juzorei/harrecon/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/juzorei/harrecon)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/harrecon)](https://pypi.org/project/harrecon/)

An agent skill and a CLI that turn a HAR capture into a private API's inventory, response schemas and a typed Python client — offline, stdlib only.

A site without documented API still has an API: its frontend calls it, and a HAR capture records every call. The usual workflow is re-reading requests by hand, forgetting a header, and debugging blind. `harrecon` does the extraction and keeps the human on the judgment calls:

```text
$ harrecon inventory capture.har
captured 5 entries, 2 JSON endpoints

auth mechanisms:
  authorization: Bearer: [redacted] (32 chars)

  GET /v1/lots/{id}  [api.example.com] 200/200

$ harrecon schema capture.har "GET /v1/lots/{id}"
object
  id: int
  title: string
  price: number

$ harrecon diff worked.har broken.har
  ~ GET /v1/lots/{id} [api.example.com] schema changed:
     $.currency: added (string)
```

## New in 0.2.0

`diff` now pinpoints added/removed fields, changed types and optionality, including nested objects and array items. Add `--fail-on-change` to return exit 1 when captures differ; the default remains report-only. JSON output includes host-qualified endpoints and machine-readable field changes while keeping full before/after schemas.

Inventory auth samples are fully masked, including short credentials. Optional fields remain optional across later samples. See the [CLI reference](tools/harrecon/README.md#field-level-diffs-020) for output and exit-code details. Differences describe observed captures, not necessarily breaking API changes.

## What's in the repo

- **[skills/har-to-api-client](skills/har-to-api-client)** — capture hygiene (Preserve log, HAR *with content*, capture the auth request), auth mechanism identification, schema inference caveats (merged samples ≠ documentation), client review, diff-based scraper debugging, and the ToS boundaries stated out loud: own account, public data, rate limits; no auth bypass.
- **tools/harrecon** — the CLI ([README](tools/harrecon/README.md)): `inventory` / `schema` / `diff` / `gen`, redacted auth output, per-endpoint typed client skeletons, offline tests on fixture captures.

## Install

```bash
pip install harrecon
npx skills add juzorei/harrecon
```

## Scope

Interoperability research on services you're authorized to use: your account, public data, throttled clients. Not for bypassing authentication or scraping against a service's rules.

MIT licensed.
