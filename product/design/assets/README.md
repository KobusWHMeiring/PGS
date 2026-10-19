# Assets — provenance and constraints

**Last Updated:** 2026-10-19
**Used by:** `product/design/final_home.html`
**Origin:** downloaded from the live site, `https://pgsouteniqua.wordpress.com/`
**Destination:** these become `core/static/img/` in MVP 0 sub-plan C. They are not final until then.

---

## 1. Why this file exists

These are **the group's own published assets**, re-used on the group's own replacement site, so
there is no third-party licensing question. But they are not versioned, not size-optimised by
anyone, and one of them has a real constraint that will bite whoever implements this. Recorded so
that is known rather than rediscovered.

**How they were obtained.** The WordPress media API is **not public** —
`/wp/v2/sites/pgsouteniqua.wordpress.com/media` returns **HTTP 401**. So the asset list came from
two places instead:

```bash
curl https://pgsouteniqua.wordpress.com/sitemap.xml          # <image:loc> entries per URL
curl https://pgsouteniqua.wordpress.com/                     # img src in the markup
```

That means **this list is not complete.** Only images referenced by a *published page* are here.
Media uploaded but never used, and anything behind the Google Drive permission wall, is invisible
to this method. If the group wants a complete library it needs media-library access.

---

## 2. What is here

### Used by the design

| File | Size | Where | What it is |
|---|---|---|---|
| `logo_mark.png` | 135×192, 17.8 KB | header (40 px), footer (48 px) | The sprout only — orange sun, lime leaf, dark-green leaf, brown leaf and root system. Cropped from the lockup at the 341 px column gap (x 0–1247). |
| `social_instagram.png` | 128×128, 11.5 KB | footer | Instagram glyph. Live account: `instagram.com/pgs_outeniqua` |
| `social_facebook.png` | 128×128, 3.4 KB | footer | Facebook glyph. Live account: `facebook.com/profile.php?id=61579994608416` |

Both social hrefs are the **real published accounts**, taken from `/news-2/`. They were previously
missing from the design entirely.

### Photographs — in use since 2026-10-19

| File | Size | Where | Subject |
|---|---|---|---|
| `mountain_scene.jpg` | 1920×846, 119 KB | **hero ground** (under the dark gradient) | Dusk mountain ridge and tree. The group's own WordPress header crop. |
| `farm_maize.jpg` | 900×675, 158 KB | farm gallery | Multicoloured heritage maize cobs on weathered wood. |
| `farm_goats.jpg` | 900×600, 118 KB | farm gallery | Goats on a farm road, wire fences, pines. |
| `farm_greens.jpg` | 700×1050, 141 KB | farm gallery | Dense beds of leafy crops. |

All four are RGB JPEG, quality 82, progressive, centre-cropped to their slot's aspect ratio. Cards
start from a `brand-sand` ground so there is no white flash before load.

**Captions name no farm.** Attribution is unconfirmed, and an invented farm name in a caption is a
factual claim about a real business. The gallery carries a visible
`farm attribution & consent to confirm` chip instead.

### Deliberately NOT used

| File | Why |
|---|---|
| `gourmet-mushroom.jpg` | A phone snapshot: cluttered background (a wall, a hand, fabric), flat lighting. Not design-grade. Recorded so nobody adds it later thinking it was overlooked. |

### Available but not placed

| File | Size | Note |
|---|---|---|
| `logo_lockup.png` | 560×201, 33.4 KB | The full lockup: mark + **PGS** + `SOUTH AFRICA` + `outeniqua`. **Not currently used — see §3.** |

### Source originals

`_source/` holds the untouched downloads, for provenance and re-export. **3.3 MB** — safe to delete
if the repo should stay lean; every file can be re-fetched with the two commands in §1.

| File | Original size | Note |
|---|---|---|
| `outeniqua-pgs-logo.png` | 4948×1775 | The master. A **print-resolution** asset, 7× larger than any web use needs. |
| `cropped-mountain-scene.jpg` | 2000×881 | WordPress header crop, used 7× on the homepage. Landscape. |
| `dsc08839.jpg` | 1080×1920 | Portrait. Used 6× on the homepage. |
| `maize-variety.jpg` | 2592×1944 | On `/about-2/`. |
| `goats-on-road.jpg` | 2000×1335 | On `/contact/`. |
| `gourmet-mushroom.jpg` | 2592×1944 | Homepage. |
| `5772032.png`, `5771766-1.png` | 128×128 | Raws of the two social glyphs. Names are WordPress-internal. |

---

## 3. The constraint that matters: **the lockup is a light-background-only asset**

The `PGS | SOUTH AFRICA` wordmark is **solid black**, and it disappears on the dark forest
surfaces the design actually uses. Measured: compositing the lockup on `brand-forest` (#323E2A)
renders the entire wordmark effectively invisible.

The design works around this by using the **mark only** on dark, and HTML text for the wordmark:

- **Header** (light `brand-cream`) — mark + `<span>` text. Crisp, translatable, and it scales,
  which the raster lockup does not.
- **Footer** (dark `brand-forestDeep`) — mark + `<h4>` text. The colour illustration reads fine on
  dark; the black wordmark would not.

**A second constraint: the lockup needs ≥400 px to be legible.** At the 187 px a header would
give it, `SOUTH AFRICA` renders about 5 px tall. It is a two-line, letterspaced wordmark — it is
not a small-size mark. So it is deliberately unplaced rather than squeezed in.

**The correct fix is to ask the designer for two derived files**, not to synthesise them:

1. **A reversed lockup** — white/cream wordmark for dark backgrounds.
2. **An SVG** of the mark and the lockup. This is flat four-colour vector artwork; the PNG is
   antialiased-alpha-heavy (33 KB for six colours, which is absurd), and an SVG would be a few KB,
   resolution-independent, and recolourable via `currentColor`.

Recolouring a logo ourselves is a brand decision, not a CSS one. Flagged, not done.

---

## 4. Seals — none were downloaded, deliberately

Worth stating plainly because it is the obvious thing to reach for: **the live site displays no
seals at all.** The two numbered PNGs that looked like they might be seals (`5772032.png`,
`5771766-1.png`) are the social glyphs.

And they must not be added, for two independent reasons:

1. **MVP 0 publishes no seal.** `MVP0_PRD.md` §3: *"…while publishing no farm status, no
   certificate, no seal and no QR code."* The four FORM outcomes and the active seals belong to
   MVP 2 (`D33`).
2. **The pasture-raised seal is inactive and is never rendered** (`D11`), with issuance
   hard-blocked and no override. `test_claim_discipline.py` will fail the build on
   `pasture raised`, `GMO free`, `biodynamic`, `chemical-free`, `spray-free`.

Note the asymmetry this leaves: the live `/endorsed-farms/` page *claims* "certified pasture
raised … GMO free" in **text**, while displaying no seal image. The claim is prose, not artwork,
which is why a grep test catches it and an image review would not. See `content_inventory.md` §5.

---

## 5. Photography — in use, consent still open

The design originally carried **no photographs at all**; the hero was a drawn SVG landscape. Four
of the group's own photographs are now placed: one as the hero ground, three in a farm gallery.

**This is not settled, and the reason is not aesthetic.** Photographs of identifiable people, farms
and households are personal data. `HANDOVER.md` §8 already lists *"POPIA consent for
already-published farmer/consumer names"* as an open item, and photographs are the same question in
a different medium. None of the four selected images shows an identifiable person — the greens
photo includes a hand — which lowers the risk but does not establish a consent basis.

Everything here was **already public** on the group's own site when downloaded. That is not the
same as consent. `DESIGN.md` §11.2 carries it.

**One measurement worth keeping.** Putting the photo in the hero introduced a real accessibility
defect, caught by sampling the rendered backdrop: as a child `<img>`, the photograph painted
*over* the gradient overlay, leaving the pale sky behind the headline at **1.05:1** contrast.
Moved into the element's own `background` stack (photo below, gradient above), it measures
**8.17:1** median and **4.93:1** worst case. Any future hero refactor must re-measure rather than
assume.

---

## 6. Reproducing the crops

```python
from PIL import Image
src = Image.open("_source/outeniqua-pgs-logo.png").convert("RGBA")
tight = lambda im, t=16: im.split()[3].point(lambda v: 0 if v < t else 255).getbbox()

lockup = src.crop(tight(src))                                  # full lockup
mark   = src.crop((0, 0, 1248, src.height))                    # left of the 341px gap
mark   = mark.crop(tight(mark))
lockup.resize((560, round(lockup.height*560/lockup.width)), Image.LANCZOS).save("logo_lockup.png", optimize=True)
mark.resize((round(mark.width*192/mark.height), 192), Image.LANCZOS).save("logo_mark.png", optimize=True)
```

The `1248` is the mark/wordmark boundary, found by scanning for the widest run of empty alpha
columns. The other gaps found (3253–3344, 3378–3455, 3557–3650) are the word spaces in
`SOUTH AFRICA`.
