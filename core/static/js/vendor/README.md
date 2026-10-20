# Vendored JavaScript

`build_principles.md` §IV: **zero build pipeline.** Every browser dependency is a
single checked-in file, loaded from this origin. Nothing comes from a CDN.

| File | Version | Source | Licence | Loaded on |
|---|---|---|---|---|
| `htmx.min.js` | 2.0.4 | `https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js` | BSD 2-Clause | `/ask/` only |

HTMX is deliberately **not** in `base.html`: 50 KB of JavaScript that a visitor reading
the fees page does not need. `core/tests/test_chatbot_surface.py` asserts it appears on
no other public route.

Updating it means replacing this one file and re-running the browser suite. There is no
lockfile, no `npm install`, and no build step to reproduce.
