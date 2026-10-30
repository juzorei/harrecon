---
name: har-to-api-client
description: Reverse-engineer a website's undocumented JSON API from a HAR capture and build a typed client from it. Use whenever the user says "there's no API", "capture the requests", "read my HAR file", "figure out what endpoint the site uses", "make a client for this site", "my scraper broke — did they change the API", asks to analyze network traffic, DevTools export, "what requests does this app make", or wants to integrate with a service that only has a web frontend. Covers capture hygiene, endpoint inventory, auth mechanism identification (Bearer/cookies/CSRF), schema inference across samples, client generation, capture diffing, rate limits and ToS boundaries. Not for bypassing authentication or scraping against a site's rules.
---

# HAR to API client

A site without documented API still has an API — its frontend calls it, and a HAR capture records every call. This skill turns a capture into an inventory, a schema, and a typed client, while keeping the reverse-engineering on the right side of the line.

## 1. Get a good capture (garbage in, nothing out)

If the user has no HAR yet, walk them through making one — most triage failures start here:

1. DevTools → Network tab → check **Preserve log** (survives navigations) and **Disable cache**.
2. Perform exactly the action whose API you want, nothing else.
3. Right-click the request list → **Save all as HAR with content** (without content there are no response bodies, and without bodies there are no schemas).

If auth matters (it usually does), the capture must include the login or token-fetch request too — otherwise the client can authenticate everything except itself.

## 2. Inventory: what API does the capture contain

```bash
harrecon inventory capture.har
```

Static assets, HTML and tracking noise are excluded automatically; numeric path ids collapse to `{id}` so repeated calls count as one endpoint. The inventory also prints which **auth mechanisms** the API actually uses (Bearer tokens, cookies, CSRF headers) with redacted samples — that tells you what your client will need before you write it.

`--host filters` to one backend when the capture spans CDNs and APIs; `--json` for scripts.

## 3. Schema: the shape of the response

```bash
harrecon schema capture.har "GET /v1/lots/{id}"
```

Schemas are merged across all samples of the endpoint: a field present in some responses only is marked `(optional)`. This is inference from captured data, not documentation — treat it as "the shape observed in this capture", and re-verify against a fresh capture before relying on a field.

## 4. Generate the client, then review it

```bash
harrecon gen capture.har "GET /v1/lots/{id}" --out client.py
```

The skeleton has dataclasses typed from the inferred schema, the captured URL, and auth header placeholders. Read it before using: the generator doesn't know which headers are load-bearing, what pagination looks like, or whether the endpoint rate-limits — that's the review.

## 5. When a scraper breaks: diff the captures

Capture the same flow twice — once when it worked, once after it broke — and:

```bash
harrecon diff worked.har broken.har
```

Endpoints added/removed and schemas changed are reported precisely. This turns "the site changed something" into a list of concrete differences, and it's the fastest way to answer "did they change the API or is my code wrong".

## 6. Play by the rules — say them out loud

Working against a private API is interoperability research only when it respects the service:

- **Your account, your data.** Authenticate as the user; never bypass auth, never touch other people's data.
- **Rate limits are a feature.** Throttle the client below the site's own frontend pace; add backoff on 429.
- **Read the ToS** for the specific service before the client ships; some prohibit any third-party access regardless of politeness.
- **Private ≠ secret.** Captured tokens stay on the user's machine — redact them in anything shared (the CLI's inventory already redacts).

When the user's goal crosses a line — bypassing auth, other people's accounts, ToS-prohibited scraping — say so plainly and offer the legitimate variant (their own account, the service's official API, or a data export).

## 7. Report

```text
api:      2 JSON endpoints on api.example.com; auth = Bearer token
schema:   GET /v1/lots/{id} → {id: int, title: string, price: number}
client:   client.py generated (dataclasses + fetch()); auth placeholder reviewed
caveats:  schema from 2 samples; verify on fresh capture before relying on `price`
```

Caveats are part of the deliverable: a schema inferred from one sample is a hypothesis, not a contract.
