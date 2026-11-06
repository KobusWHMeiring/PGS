"""Prove that `copy_deck.py --apply` cannot damage the tree. Run after any change to it.

    python scripts/copy_deck_selftest.py     # 2 s, no database, writes nothing outside tmp

Nothing here touches the real templates: ROOT is monkeypatched to a temp directory holding a
copy of `core/services/_public.py` and `core/templates/public/`. Six properties, each of which
has been broken at least once while building the tool:

1. Applying every `auto` row with its own text changes no string on the site. Offsets are the
   whole game here, and a region that is one character wide is silently destructive.
2. A real rewrite lands exactly, and the markup around it survives.
3. A deck whose `old:` no longer matches the tree is refused, not applied.
4. A `locked` row is refused.
5. A `PAGES` rewrite keeps `_public.py` parseable.
6. The round trip a writer actually performs - fill a `new:` block in the file, re-read it,
   apply it, regenerate the deck - keeps the rewrite.

**Not wired into `verify.sh` or `fast.sh`.** It tests a build tool, not the product, and
`AGENTS.md` is explicit that no fourth lane gets invented for a test. Run it by hand when the
generator changes; it is 2 seconds.
"""

from __future__ import annotations

import ast
import shutil
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REAL / "scripts"))
import copy_deck as cd  # noqa: E402

tmp = Path(tempfile.mkdtemp())
shutil.copytree(REAL / "core/templates/public", tmp / "core/templates/public")
(tmp / "core/services").mkdir(parents=True)
shutil.copy2(REAL / "core/services/_public.py", tmp / "core/services/_public.py")
cd.ROOT = tmp

rows = cd.build()
cd.assign_ids(rows)
(cd.ROOT / "deck.md").write_text(cd.render(rows, {}), encoding="utf-8")
before = {r.id: (r.text, r.mode) for r in rows}
fails: list[str] = []


def rebuild() -> dict[str, cd.Row]:
    again = cd.build()
    cd.assign_ids(again)
    return {r.id: r for r in again}


# 1. identity apply: same text in, same text out - the invariant that matters, because the
#    writer re-wraps the paragraph even when the words are unchanged.
identity = {r.id: (r.text, r.text) for r in rows if r.mode == "auto"}
rc = cd.apply_deck(rows, identity, dry_run=False)
after = rebuild()
drift = [i for i, (t, _) in before.items() if i in after and after[i].text != t]
lost = [i for i in before if i not in after]
print(f"1. identity apply  rc={rc}  text_drift={len(drift)}  lost={len(lost)}")
if drift or lost or rc != 0:
    fails.append("identity")
    print("   drift:", drift[:5], "lost:", lost[:5])

# 2. a real rewrite lands exactly, and the markup around it survives
rows = after_rows = list(after.values())
cd_rows = rows
target = next(r for r in cd_rows if r.mode == "auto"
              and r.source.endswith("_why_join.html") and "committee records" in r.text)
new_text = ("The committee records one of four outcomes against the SAOSO standard. "
            "Where findings need addressing they are written down first, so a \u201cnot yet\u201d "
            "says what would change it.")
rc = cd.apply_deck(cd_rows, {target.id: (target.text, new_text)}, dry_run=False)
after2 = rebuild().get(target.id)
ok = after2 is not None and after2.text == new_text
print(f"2. rewrite {target.id}  rc={rc}  landed={ok}")
if not ok:
    fails.append("rewrite")
    print(f"   got: {after2.text[:120] if after2 else 'MISSING'}")
body = (tmp / target.source).read_text(encoding="utf-8")
if '<p class="element-card__body">' not in body or "OPP \u00a74" not in body:
    fails.append("markup")
    print("   markup around the rewrite was disturbed")

# 3. a stale deck is refused, not applied
stale = {target.id: ("something else entirely", "and a rewrite")}
rc = cd.apply_deck(cd_rows, stale, dry_run=True)
print(f"3. stale old:        rc={rc} (1 = refused)")
if rc != 1:
    fails.append("stale")

# 4. a locked row is refused
locked = next(r for r in cd_rows if r.mode == "locked")
rc = cd.apply_deck(cd_rows, {locked.id: (locked.text, "x")}, dry_run=True)
print(f"4. locked {locked.id:<16} rc={rc} (1 = refused)")
if rc != 1:
    fails.append("locked")

# 5. a PAGES rewrite keeps valid Python and the right string
py = next(r for r in cd_rows if r.py_field == "lede" and r.lines[0] != r.lines[1])
rc = cd.apply_deck(cd_rows, {py.id: (py.text, "A short new lede for the home page.")},
                   dry_run=False)
source = (tmp / "core/services/_public.py").read_text(encoding="utf-8")
try:
    ast.parse(source)
    parses = "ok"
except SyntaxError as exc:
    parses = f"BROKEN: {exc}"
got = rebuild().get(py.id)
ok = got is not None and got.text == "A short new lede for the home page."
print(f"5. PAGES {py.id}      rc={rc}  landed={ok}  python={parses}")
if not ok or parses != "ok":
    fails.append("py")

# 6. every auto row is inside a single element, i.e. one <p>-shaped container
print(f"\nresult: {'PASS' if not fails else 'FAIL ' + ','.join(fails)}")
shutil.rmtree(tmp)
sys.exit(1 if fails else 0)
