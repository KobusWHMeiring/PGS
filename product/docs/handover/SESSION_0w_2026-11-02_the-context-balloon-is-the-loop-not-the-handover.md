## 0w. 2026-11-02 (session 9) — the context balloon is the loop, not the handover

**What was asked.** The owner reported **1.8 M-token contexts for relatively few turns** and asked
for a high-level investigation. Changing the Pi compaction setting was explicitly out of scope.

**What was measured.** The 47 session logs under
`~/.pi/agent/sessions/--C--Users-Kobus-Meiring-Documents-Dev-pgs--/` (2026-10-18 → 2026-11-02),
read by a script that sums `usage` per request and classifies every content block.

| Measurement | Value |
|---|---:|
| Cumulative tokens processed | **1,704,598,340** (1.70 B) |
| Median per session | **26.4 M** |
| Worst session | **121.9 M** (457 requests) |
| Median user messages per session | **7** |
| Median API requests per session | **181** |
| Requests per user message (median) | **26.5** |
| Context growth per request (median) | **+1,009 tokens** |
| Largest single live context | **562,454** |
| Automatic compactions in 47 sessions | **0** |

**The finding, in one line: the figure is cumulative, not one context.** The largest single request
in the PGS logs is 562k; across every project on this box it is 609k. What is 1.8 M is the sum over
requests: a tool call is a new request that re-sends the whole conversation, so
`cumulative ≈ requests × average context`. This session demonstrated it — one user message, 32
requests, **1.4 M tokens**, while its live context never passed **75k**.

**Where the retained bytes are** (text only; chars/4 ≈ tokens): tool results 37% (16.1 MB),
thinking 30% (13.3 MB), tool-call arguments 30% (13.2 MB), assistant prose 3%. Two-thirds of the
transcript is the agent's own output. The habits behind those numbers:

- `cat`/`sed`/`head`/`tail`: **3,769 calls / 8.5 MB**.
- `python - <<'PY'` heredocs: **1,492**; each script body stays in the transcript.
- `write`: 372 calls / 4.46 MB (avg 12 KB); `edit`: 1,103 calls / 2.69 MB.
- Images: **189 reads / 51.6 MB base64**; `home-desktop.png` was read 10 times. Pi estimates an
  image at 1,200 tokens, so this is real but secondary — one session reached 76k image tokens.

**Why nothing stopped it.** `opencode-go/deepseek-v4.1-flash` declares a **1,000,000-token** context
window, so auto-compaction triggers only above **983,616** (`reserveTokens` 16,384). None of the 47
sessions reached it; the long ones simply ended. The read-set cuts in `CONTEXT_BUDGET.md` make each
request cheaper; they do not reduce the number of requests.

**What was changed.**
- `AGENTS.md` — the "read these first" table became a shelf plus a recipe pointer, and a new
  **Context discipline** block carries the six rules above with the measured numbers.
- `product/docs/context/CONTEXT_BUDGET.md` — new §7 records the loop measurement and the habits.
- `scripts/context.py` — printed output is now ASCII. It had been dying on `≈` in the read-budget
  line on this box's cp1252 console, i.e. every recipe crashed at the last line (third instance of
  `testing_hazards.md` §3.21). The stale "101 lines" descriptions are gone.
- `tests/tools/test_context.py` — guards that every recipe path exists, every recipe prints a
  budget, the output is ASCII, and `--check` reports without crashing.

**What was deliberately not changed.** The Pi compaction setting (`reserveTokens`), per the owner.
That is the one change that would cap a session mechanically; it stays on the table for later.

**Checked.** `scripts/verify.sh` — **1566 passed, 1 skipped in 133.93 s** cold (the new
`tests/tools/test_context.py` is in the gate). `scripts/fast.sh --critical` — 208 passed, 4
deselected, 11-18 s across three runs; `tests/tools` minus `slow` — 160 passed, 1 deselected in
6.10 s. The full gate was run for this change and passed.

**What the next session should know.** The read-set was never the whole bill. Before adding a new
"read this first" line, ask how many requests it will be re-sent in. And keep terminal reports
ASCII — the console is cp1252, and an instrument that crashes on a glyph is a tool people stop
running.
