"""Pull the prose from the SAOSO and PGS websites into one reference file.

    python scripts/fetch_reference_copy.py            # fetch, then write the corpus
    python scripts/fetch_reference_copy.py --refresh  # ignore the cache, re-fetch everything
    python scripts/fetch_reference_copy.py --check    # show the summary table only

Writes `product/design/REFERENCE_COPY_CORPUS.md`: for every page, where it came from, when,
how long, and the text. Four sources:

* **SAOSO** (`www.saoso.org`) - the national umbrella body whose standard this group assesses
  against. Its register is the one a PGS committee already trusts.
* **PGS South Africa** (`www.pgssa.org.za`) - the national PGS body. Note the parked domain
  `pgssa.co.za` is *not* it; the real one is linked from saoso.org.
* **Western Cape Farmer's PGS** (`pgs.org.za`) - a sibling group in the same province, so the
  closest thing to a peer voice that exists.
* **IFOAM Organics International** - the definition of a PGS that SAOSO adopts and this site
  quotes.

**What this file is for, and what it is not for.** It exists to be *searched* for how these
bodies actually say things - the register, the sentence length, the words for a visit, a
decision, a member. It is **not** a source of truth for what this group may claim. Every page
here is flagged for the phrases `core/tests/test_claim_discipline.py` forbids, because an
umbrella body's marketing copy routinely says things a PGS group may not repeat. The sources of
truth remain `pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf` and
`pgs_docs/saoso-version-2.1-2026.pdf`.

**Provenance is per page and is in the file**, because a quote with no URL and no date is
indistinguishable from an invention. The fetch date is today's, and the cache lives in
`_scratch/reference_html/` so a re-run does not hammer anyone's server.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path("product/design/REFERENCE_COPY_CORPUS.md")
CACHE = ROOT / "_scratch" / "reference_html"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

#: Snapshot of `core.services._public.FORBIDDEN_CLAIMS`, which
#: `core/tests/test_claim_discipline.py` guards. Duplicated rather than imported because this
#: is a build script and importing `core` would drag Django settings into a network tool.
FORBIDDEN = ("pasture raised", "pasture-raised", "gmo free", "gmo-free", "biodynamic",
             "chemical-free", "spray-free")

#: (source label, url, why this page is worth having). Reading order: the body whose standard
#: it is, then the national PGS body, then a sibling group, then the definition.
PAGES: tuple[tuple[str, str, str], ...] = (
    # -- SAOSO ------------------------------------------------------------------
    ("SAOSO", "https://www.saoso.org/", "home - the register the sector body opens with"),
    ("SAOSO", "https://www.saoso.org/about-us/", "who SAOSO is, and what it claims to do"),
    ("SAOSO", "https://www.saoso.org/what-we-do/", "the four or five things it lists as its work"),
    ("SAOSO", "https://www.saoso.org/organic-certification/",
     "how the sector body explains assurance - the closest thing to our own page's job"),
    ("SAOSO", "https://www.saoso.org/choose-organic/", "consumer-facing persuasion, for contrast"),
    ("SAOSO", "https://www.saoso.org/faq/", "question-and-answer register"),
    ("SAOSO", "https://www.saoso.org/membership/", "how a body asks people to join"),
    ("SAOSO", "https://www.saoso.org/knowledge-hub/why-organic/", "the why-organic argument"),
    ("SAOSO", "https://www.saoso.org/knowledge-hub/farmer-hub/", "farmer-facing hub"),
    ("SAOSO", "https://www.saoso.org/knowledge-hub/farmer-hub/converting-to-organic/",
     "conversion guidance - plain instruction, the OPP's own register"),
    ("SAOSO", "https://www.saoso.org/contact/", "how a body ends a page"),

    # -- PGS South Africa -------------------------------------------------------
    ("PGS SA", "https://www.pgssa.org.za/", "home"),
    ("PGS SA", "https://www.pgssa.org.za/about-us/", "who the national PGS body is"),
    ("PGS SA", "https://www.pgssa.org.za/what-we-do/", "its work, in its own words"),
    ("PGS SA", "https://www.pgssa.org.za/our-work/", "a second pass at the same subject - "
     "compare with /what-we-do/ for which version reads as written rather than generated"),
    ("PGS SA", "https://www.pgssa.org.za/organic-certification/",
     "PGS versus third-party certification, explained by the body"),
    ("PGS SA", "https://www.pgssa.org.za/why-organic/", "the pitch"),
    ("PGS SA", "https://www.pgssa.org.za/find-organic-food/", "the member-list surface"),
    ("PGS SA", "https://www.pgssa.org.za/membership/", "joining, and what it costs"),
    ("PGS SA", "https://www.pgssa.org.za/resources/", "resource index"),
    ("PGS SA", "https://www.pgssa.org.za/training-page/", "training offer"),
    ("PGS SA", "https://www.pgssa.org.za/the-market/", "market-facing copy"),
    ("PGS SA",
     "https://www.pgssa.org.za/how-pgs-groups-organise-for-market-and-integrity-of-production/",
     "the most useful page here: a national body describing PGS procedure in prose"),
    ("PGS SA", "https://www.pgssa.org.za/making-pgs-groups-sustainable/",
     "sustainability of a group, in prose"),
    ("PGS SA", "https://www.pgssa.org.za/the-challenge-of-honouring-the-fundamentals-of-pgs/",
     "self-critical prose - the voice a committee recognises"),

    # -- Western Cape Farmer's PGS ---------------------------------------------
    ("Cape PGS", "https://pgs.org.za/", "a sibling group in the same province"),
    ("Cape PGS", "https://pgs.org.za/farmers/", "how a peer group lists its farmers"),
    ("Cape PGS", "https://pgs.org.za/documentation/", "what a peer group publishes as its rules"),
    ("Cape PGS", "https://pgs.org.za/resources/", "peer resource page"),
    ("Cape PGS", "https://pgs.org.za/contact/", "peer contact page"),

    # -- IFOAM ------------------------------------------------------------------
    ("IFOAM", "https://www.ifoam.bio/our-work/how/standards-certification/"
              "participatory-guarantee-systems", "the definition this site quotes"),
    ("IFOAM", "https://www.ifoam.bio/our-work/how/standards-certification/"
              "participatory-guarantee-systems/pgs-toolkit", "the PGS toolkit"),
)

#: Elements whose text is never the article.
SKIP = frozenset({"script", "style", "noscript", "nav", "header", "footer", "aside",
                  "form", "button", "select", "option", "svg", "iframe", "figure",
                  "template", "dialog"})

#: Elements that end a paragraph.
BLOCK = frozenset({"p", "div", "section", "article", "main", "li", "h1", "h2", "h3", "h4",
                   "h5", "h6", "br", "tr", "td", "th", "blockquote", "dt", "dd", "main"})

MAX_WORDS = 1600


@dataclass
class Fetched:
    label: str
    url: str
    why: str
    status: int = 0
    title: str = ""
    text: str = ""
    words: int = 0
    claims: tuple[str, ...] = ()
    note: str = ""
    digest: str = ""


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth_skip = 0
        self.pieces: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.depth_skip += 1
            return
        if tag == "title":
            self._in_title = True
        if tag in BLOCK:
            self.pieces.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.depth_skip = max(0, self.depth_skip - 1)
            return
        if tag == "title":
            self._in_title = False
        if tag in BLOCK:
            self.pieces.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
            return
        if not self.depth_skip:
            self.pieces.append(data)


def _clean(raw: str) -> str:
    """Paragraphs a reader would call the article, with the furniture dropped."""
    lines = []
    for chunk in raw.split("\n"):
        line = re.sub(r"\s+", " ", chunk).strip(" |·•\u00a0")
        if len(line) < 20:
            continue                      # nav labels, breadcrumbs, "Read more"
        if line.count(" ") < 3:
            continue                      # menu rows
        lines.append(line)

    # drop runs repeated verbatim (Divi/Elementor repeat the same CTA block per section)
    seen: set[str] = set()
    kept = []
    for line in lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(line)

    text = "\n\n".join(kept)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])
        text = re.sub(r"(?<=[.!?]) (?=[A-Z])", "\n\n", text)
    return text


def fetch(label: str, url: str, why: str, refresh: bool) -> Fetched:
    got = Fetched(label=label, url=url, why=why)
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.html"
    try:
        if cached.exists() and not refresh:
            html = cached.read_text(encoding="utf-8", errors="replace")
            got.note = "cached"
        else:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                got.status = resp.status
                html = resp.read().decode(resp.headers.get_content_charset() or "utf-8",
                                          errors="replace")
            cached.write_text(html, encoding="utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        got.note = f"failed: {type(exc).__name__}: {exc}"
        return got

    parser = _Text()
    parser.feed(html)
    got.title = re.sub(r"\s+", " ", parser.title).strip()
    got.text = _clean("".join(parser.pieces))
    got.words = len(got.text.split())
    low = got.text.lower()
    got.claims = tuple(sorted({c for c in FORBIDDEN if c in low}))
    got.digest = hashlib.sha1(re.sub(r"\W+", " ", got.text.lower()).encode()).hexdigest()
    return got


def render(pages: list[Fetched], today: str) -> str:
    ok = [p for p in pages if p.text]
    total = sum(p.words for p in ok)
    flagged = [p for p in ok if p.claims]

    out = [
        "# Reference copy corpus - SAOSO and PGS websites",
        "",
        f"**Fetched {today}** by `scripts/fetch_reference_copy.py`. Regenerate with that script;",
        "`--refresh` re-fetches, otherwise it re-reads `_scratch/reference_html/`.",
        "",
        "| | |",
        "|---|---|",
        f"| pages | {len(ok)} of {len(pages)} |",
        f"| words | {total} |",
        f"| pages carrying a forbidden claim | {len(flagged)} |",
        "",
        "## How to use this file",
        "",
        "**Search it, do not read it.** It is a register sample, not an argument. When a sentence",
        "in `COPY_DECK.md` needs rewriting and you want to know how a PGS body actually phrases",
        "that thing, `rg` for the noun here - `visit`, `decision`, `member`, `committee`,",
        "`assessment` - and read two or three lines around the hit. That is the whole method.",
        "",
        "**It is not a source of truth for what this group may claim.** Three of these sites are",
        "umbrella bodies or marketing surfaces, and they say things a single PGS group may not",
        "repeat. The forbidden-claim column below is why: `pasture raised`, `GMO free`,",
        "`biodynamic`, `chemical-free` and `spray-free` are producer statements, never PGS",
        "endorsements, and `core/tests/test_claim_discipline.py` fails the build on all of them.",
        "The sources of truth stay the OPP and the SAOSO standard, both in `pgs_docs/`.",
        "",
        "**What it is genuinely good for**, in order: (1) the words for a procedure - these",
        "bodies use `visit`, `committee`, `outcome`, `pledge`, and so should we; (2) sentence",
        "length and paragraph length in an organisation that is not selling anything; (3) the",
        "sound of a body admitting a hard thing, which is on the PGS SA self-critical pages.",
        "",
        "**What it will pull you into if you are careless:** the tricolon, the abstract headline,",
        "and the adjective. Several of these pages read as generated. Being *as good as* them is",
        "not the bar; being plainer than them is.",
        "",
        "## Three things this corpus shows, so you do not have to find them",
        "",
        "1. **The assurance vocabulary differs, and ours is the stricter one.** The Western Cape",
        "   group writes *\"Verify which farmers have been certified by the Western Cape Farmers'",
        "   PGS\"*. This group may not: membership is not certification, and MVP 0 publishes no",
        "   seal and no farm status. Read their pages for *procedure*, never for status words.",
        "2. **The tells are not machine-only.** The sibling group's opening is a textbook",
        "   tricolon - *\"through trust, transparency, and peer-to-peer collaboration\"* - and its",
        "   best sentence is a negate-then-assert: *\"Each farm is visited at least once a year -",
        "   not only to uphold standards, but also to share knowledge and strengthen connections.\"*",
        "   Written by a person. So the rule in `COPY_VOICE.md` is a budget, not a ban: one such",
        "   move per page is a voice, four is a template.",
        "3. **Where these bodies are plainest is in procedure.** The PGS SA session write-ups and",
        "   the SAOSO conversion guidance use short declaratives and no adjectives, because they",
        "   are describing what happens. That is the register to search for when a deck string is",
        "   about a visit, a decision or a fee.",
        "",
        "## Index",
        "",
        "| source | page | words | claims |",
        "|---|---|---|---|",
    ]
    for p in pages:
        name = p.title or p.url.rsplit("/", 2)[-2] or "home"
        claims = ", ".join(p.claims) if p.claims else "-"
        if not p.text:
            out.append(f"| {p.label} | {p.url} | _not fetched_ | {p.note} |")
            continue
        out.append(f"| {p.label} | [{name}]({p.url}) | {p.words} | {claims} |")

    current = None
    seen_digest: dict[str, str] = {}
    for p in pages:
        if p.label != current:
            current = p.label
            out.append(f"\n---\n\n# {current}\n")
        out.append(f"## {p.title or p.url}")
        out.append("")
        out.append(f"`{p.url}` - {p.label} - fetched {today} - {p.words} words")
        out.append("")
        out.append(f"*Why this page is here:* {p.why}")
        if p.claims:
            out.append("")
            out.append(f"> **Contains a phrase the build forbids: {', '.join(p.claims)}.** The "
                       "check is a plain substring search, so it may be a false positive - a "
                       "member association's name, for instance. Find the sentence and judge "
                       "it; do not copy it either way.")
        if p.digest in seen_digest:
            out.append("")
            out.append(f"> **Identical text to {seen_digest[p.digest]}** - the umbrella body and "
                       "the national body publish the same page. Not duplicated below.")
            out.append("")
            continue
        seen_digest[p.digest] = p.url
        if not p.text:
            out.append("")
            out.append(f"**Not fetched.** {p.note}")
            out.append("")
            continue
        out.append("")
        for para in p.text.split("\n\n"):
            out.append(para)
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="ignore the cache")
    ap.add_argument("--check", action="store_true", help="print the table, write nothing")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    today = dt.date.today().isoformat()
    pages = []
    for i, (label, url, why) in enumerate(PAGES, 1):
        got = fetch(label, url, why, refresh=args.refresh)
        flag = "" if got.text else "  <-- " + got.note
        claims = f"  claims: {', '.join(got.claims)}" if got.claims else ""
        print(f"  [{i:2d}/{len(PAGES)}] {got.status or '---'} {got.words:5d}w  "
              f"{label:<9} {url}{claims}{flag}")
        pages.append(got)

    missed = [p for p in pages if not p.text]
    out = ROOT / args.out
    if not args.check:
        out.write_text(render(pages, today), encoding="utf-8")
        words = sum(p.words for p in pages if p.text)
        print(f"\nfetch_reference_copy: wrote {args.out} - "
              f"{len(pages) - len(missed)}/{len(pages)} pages, {words} words")
    if missed:
        print(f"  {len(missed)} page(s) not fetched; they are listed as such in the file")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
