"""Task C2 — `/documents/`: the files the group publishes, at stable addresses.

**The count is eight, not seven.** `MVP0_PLAN_V2.md` C2 says "exactly seven items
(D22)" and then enumerates eight: SAOSO v2.1, the OPP, the Basic Production
Principles, the Certification Landscape, the visit preparation list, and the three
participant checklists. `pgs_docs/` confirms eight files. D22's ninth — the
assessment workbook (`…summary_2026.xlsx`) — is excluded until the committee
confirms it, and `test_the_assessment_workbook_is_not_published` keeps it excluded.
`C1_BUILD_PLAN.md` §6 #6 assumed SOP's *is* the OPP, which is what keeps the count
at eight; if that assumption is overturned the list grows and this docstring is
wrong, not the code.

Three rules this file exists to enforce:

1. **Every published document downloads, and the bytes are the shipped bytes.** The
   published copy is compared to `pgs_docs/<source>` by sha256. A deploy that copies
   the wrong file, or truncates one, is the failure that looks fine in a browser.
2. **Unpublished and unknown documents are indistinguishable.** Both 404 from the
   same query. D22's dossiers contain farmer personal data, so "not in the list" and
   "not reachable at a guessed URL" have to be the same guarantee.
3. **A missing file fails loudly.** A 404 would say "we never published this", which
   is a lie about a document the home page links to; the view answers 503 and logs.

Media is redirected to `tmp_path` for the whole module. The `publish_documents`
command is idempotent on sha256, so only the first invocation in a session copies
bytes — every later one is the idempotency check for free.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import Client

from core.models import PublicDocument
from core.services._documents import DOCUMENTS

pytestmark = pytest.mark.django_db

DOCS_SOURCE = Path("pgs_docs")


# --- Publishing the files ---------------------------------------------------


@pytest.fixture(scope="session")
def documents_media(tmp_path_factory):
    """One directory per session: copying 8.6 MB per test would be the cost of nothing."""
    return tmp_path_factory.mktemp("media")


@pytest.fixture
def published(settings, documents_media):
    settings.MEDIA_ROOT = documents_media
    call_command("publish_documents", verbosity=0)
    return documents_media


@pytest.fixture
def codes() -> list[str]:
    return [spec.code for spec in DOCUMENTS]


def test_the_list_is_eight_documents_and_has_the_right_sources():
    """The guard-the-guard: `DOCUMENTS` drives every parametrised test below.

    An empty or truncated tuple would make the download tests run zero-to-few cases
    and report success (`testing_hazards.md` §1.6). The source paths are asserted to
    exist because a stale filename in a Python constant fails at deploy, not at
    import, and by then `/documents/` is already live.
    """
    assert len(DOCUMENTS) == 8, f"expected 8 published documents, found {len(DOCUMENTS)}"
    for spec in DOCUMENTS:
        assert (DOCS_SOURCE / spec.source).is_file(), f"{spec.code}: missing {spec.source}"


def test_the_recorded_source_is_the_path_a_citation_joins_on(published):
    """`source_path` must equal the corpus's `source_file`, or no citation is clickable.

    The absolute path `source.as_posix()` used to record is wrong twice over: it differs per
    machine, and it can never equal `StandardDocument.source_file` (`pgs_docs/<file>.pdf`),
    which is the only join between a stored chunk and a public address. Asserted against the
    published row the seed wrote, not against a literal, so the constant and the seed cannot
    drift apart silently.
    """
    from core.services._documents import DOCUMENTS, DOCS_SOURCE_DIR, public_codes_by_source

    row = PublicDocument.objects.get(code="saoso-standard-v2.1")
    expected = (DOCS_SOURCE_DIR / DOCUMENTS[0].source).resolve()
    repo_relative = expected.relative_to(Path(settings.BASE_DIR).resolve()).as_posix()

    assert row.source_path == repo_relative
    assert public_codes_by_source()[repo_relative] == "saoso-standard-v2.1"


def test_publish_is_idempotent(published):
    """It runs on every deploy, so a second run must create and update nothing.

    Not a nicety: the command rewrites rows from specs, and a re-run that "updates"
    every row on every deploy would silently undo any change the group made in the
    admin — the same rule `seed_deployment` follows for `is_active`.
    """
    first = PublicDocument.objects.count()
    result = call_command("publish_documents", verbosity=0)

    assert PublicDocument.objects.count() == first, "a re-run duplicated rows"
    assert "created=0" in result, f"a re-run created rows: {result!r}"
    assert "updated=0" in result, f"a re-run rewrote rows: {result!r}"
    # The bytes are compared by sha256, so a re-run must not rewrite 8.6 MB either. An
    # always-copy implementation passes the two assertions above and still costs a
    # full disk write per deploy — invisible until the disk is full.
    assert "copied=0" in result, f"a re-run recopied the files: {result!r}"
    assert "unchanged=8" in result, f"a re-run did not recognise its own copies: {result!r}"


def test_the_published_copy_is_byte_for_byte_the_shipped_document(published):
    """sha256 of the served file == sha256 of `pgs_docs/<source>`.

    `testing_hazards.md` §3.7: a fixture that is not the document it claims to
    describe makes every test above it decorative. The same holds for a published
    copy — "it downloaded and it starts with %PDF" is not evidence that it is the
    standard.
    """
    for spec in DOCUMENTS:
        source = DOCS_SOURCE / spec.source
        served = published / PublicDocument.objects.get(code=spec.code).file_path
        assert served.is_file(), f"{spec.code}: not copied to {served}"
        assert hashlib.sha256(served.read_bytes()).hexdigest() == hashlib.sha256(
            source.read_bytes()
        ).hexdigest(), f"{spec.code}: the served file is not {spec.source}"


# --- Downloading ------------------------------------------------------------


@pytest.mark.parametrize("code", [spec.code for spec in DOCUMENTS])
def test_every_published_document_downloads(client: Client, published, code: str):
    """200, a non-zero body, the right `Content-Type`, and a real PDF header."""
    response = client.get(f"/documents/{code}/")

    assert response.status_code == 200, f"{code} -> {response.status_code}"
    body = b"".join(response.streaming_content)
    assert len(body) > 0, f"{code} served an empty file"
    assert len(body) == int(response["Content-Length"]), f"{code}: truncation"
    assert response["Content-Type"] == "application/pdf", (
        f"{code} served as {response['Content-Type']!r} — a browser would download it "
        "as octet-stream or, worse, render a PDF as text"
    )
    assert body[:5] == b"%PDF-", f"{code} is not a PDF despite its content type"
    assert "attachment" in response["Content-Disposition"], (
        f"{code} is served inline — the page's action says Download"
    )


@pytest.mark.parametrize("code", [spec.code for spec in DOCUMENTS])
def test_the_saved_filename_is_the_documents_name(client: Client, published, code: str):
    """The browser saves `SAOSO-Organic-Standard-v2.1.pdf`, not `saoso-standard-v2.1.pdf`.

    A code is a URL segment; a filename is what a farmer files. Derived from the code it
    would be `checklist-crops.pdf` — accurate, unfindable, and the kind of detail that is
    only ever noticed by the person who has to use it.
    """
    spec = next(s for s in DOCUMENTS if s.code == code)
    disposition = client.get(f"/documents/{code}/")["Content-Disposition"]

    assert spec.download_name in disposition, disposition
    assert f'filename="{code}.' not in disposition, "the filename is the URL code"
    assert spec.download_name.endswith(".pdf")


def test_no_document_is_served_from_a_media_path(client: Client, published):
    """The URL is the code, not a storage path.

    `content_inventory.md` §4 makes the WordPress cutover a redirect table, and a
    `/media/…` URL cannot be redirected to a code; it also exposes the storage layout
    and lets `DEBUG=True` serve an unpublished file without consulting `is_published`.
    """
    html = client.get("/documents/").content.decode()
    assert "/media/" not in html, "a document is linked by media path"
    assert client.get("/documents/saoso-standard-v2.1/").status_code == 200


# --- What must never be reachable ------------------------------------------


def test_an_unpublished_document_is_not_reachable(client: Client, published):
    """Same 404 as a guessed code — D22's dossiers live behind this.

    The row exists and its file is on disk; the *only* thing standing between the
    public and it is `is_published`. That is the guarantee, and it is asserted on a
    row rather than on a document that was never created, because the latter would
    pass with the filter removed.
    """
    row = PublicDocument.objects.create(
        code="dossier-test",
        # Deliberately unlike any prose on the page: the first version of this test used
        # "Farm visit report", which the lede's "Farm visit reports and application
        # dossiers are never published" already contained — a test passing for the wrong
        # reason (testing_hazards.md §0).
        title="Dossier TEST-MARKER-2024",
        note="Personal data",
        file_path="public/documents/saoso-standard-v2.1.pdf",
        source_path="pgs_docs/saoso-version-2.1-2026.pdf",
        content_type="application/pdf",
        display_order=99,
        is_published=False,
    )
    assert (published / row.file_path).is_file(), "the fixture file is missing"

    assert client.get("/documents/dossier-test/").status_code == 404
    assert "TEST-MARKER-2024" not in client.get("/documents/").content.decode()


def test_an_unknown_code_404s(client: Client, published):
    assert client.get("/documents/no-such-document/").status_code == 404


def test_the_assessment_workbook_is_not_published(client: Client, published):
    """D22: the workbook is included *only after the committee confirms it*.

    No confirmation exists, so it is excluded. Asserted against the rows and the
    page, because the tempting shortcut — "ingest the whole folder" — would publish a
    spreadsheet of farmer answers.
    """
    assert not PublicDocument.objects.filter(title__icontains="workbook").exists()
    for spec in DOCUMENTS:
        assert not spec.source.endswith(".xlsx"), f"{spec.code} is the workbook"

    html = client.get("/documents/").content.decode().lower()
    assert "workbook" not in html
    assert "xlsx" not in html


def test_a_missing_file_is_a_loud_failure_not_a_404(client: Client, published):
    """503, because the document *is* published and the home page links to it.

    A 404 would tell the reader the document does not exist; a 500 would leak a
    traceback to a public visitor. This is `build_principles.md` §VII.5 — fail
    loudly — applied to a file that vanished between deploy and request.
    """
    served = published / PublicDocument.objects.get(code="checklist-crops").file_path
    served.unlink()

    response = client.get("/documents/checklist-crops/")
    assert response.status_code == 503, (
        f"missing file answered {response.status_code}; published-but-absent is not a 404"
    )


# --- The pages that carry the list -----------------------------------------


def test_the_documents_page_lists_every_published_document(client: Client, published):
    html = client.get("/documents/").content.decode()

    for spec in DOCUMENTS:
        assert spec.title.replace("&", "&amp;") in html, f"{spec.code} is not listed"
        assert f'href="/documents/{spec.code}/"' in html, f"{spec.code} has no download link"

    assert "Publishing soon" not in html, "a published document still shows a pending chip"


def test_the_home_page_rows_link_to_the_documents(client: Client, published):
    """C2's acceptance condition: the chips become real links in the same commit.

    The home page's band said "stable addresses you can bookmark and cite" while every
    row read `Publishing soon`. Both halves are asserted here — the link exists, and
    the placeholder is gone — because fixing one and not the other is exactly the
    half-finished state this test is for.
    """
    html = client.get("/").content.decode()

    assert "Publishing soon" not in html, "the home page still shows a pending chip"
    for spec in DOCUMENTS:
        assert f'href="/documents/{spec.code}/"' in html, f"{spec.code} is not linked from home"


def test_the_header_offers_documents(client: Client, published):
    """The nav is a promise that every published thing is one click away.

    Asserted on the rendered nav element rather than on the `NAV` tuple, because a
    route added to the tuple and dropped by the template would still pass.
    """
    html = client.get("/").content.decode()
    nav = html.split('<nav class="site-nav"', 1)[1].split("</nav>", 1)[0]
    assert 'href="/documents/"' in nav
    assert "Documents" in nav


def test_dossiers_stay_behind_request_access(client: Client, published):
    """DESIGN §7.8 / D22: the gated row's action reads `Request access`, never `Download`.

    Asserted on the gated block itself — its link target is the contact page and no
    document URL — because a whole-page `"Request access" in html` check stayed green
    when the gated row's href was changed to a download (the same false-positive shape
    as `test_home_carries_the_membership_is_not_certification_disclaimer`).
    """
    html = client.get("/documents/").content.decode()
    assert "doc-row--gated" in html, "the gated row is gone — D22's line is not drawn"

    gated = html.split("doc-row--gated", 1)[1]
    gated_block = gated.split("</a>", 1)[0]
    assert "Request access" in gated_block, "the gated action is not Request access"
    assert "/documents/" not in gated_block, "a dossier row links to a download"
    assert 'href="/contact/"' in gated_block, "the gated row does not offer a next step"


# --- The concordance, offered from the row (DOCUMENTS_READER_LINK_PRD) -------

#: The four documents whose text is ingested, so `/documents/<code>/read/` renders. The
#: other four are forms and checklists published as files, with no text to read.
WITH_TEXT = (
    "saoso-standard-v2.1",
    "opp",
    "basic-production-principles",
    "certification-landscape",
)


@pytest.fixture
def ingested(published):
    """A corpus behind four of the eight rows, joined the way the real one is.

    `StandardDocument.source_file` and `PublicDocument.source_path` must be the **same
    string** — that equality is the join the reader uses, so a fixture that faked it
    would prove nothing about the thing that breaks. One chunk per document is enough to
    make "has text" true; the real 319 are ingested by the reader's own suite.
    """
    from knowledge.models import DocumentChunk, StandardDocument, StandardSet

    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    for code in WITH_TEXT:
        document = PublicDocument.objects.get(code=code)
        twin = StandardDocument.objects.create(
            standard_set=corpus,
            kind=StandardDocument.Kind.STANDARD,
            title=document.title,
            source_file=document.source_path,
            sha256=f"{code:0<64}".replace("-", "a")[:64],
            section_scheme="saoso",
        )
        DocumentChunk.objects.create(
            document=twin, section_ref="S1", page=22, text="A definition a reader can quote."
        )
    return published


def test_the_rows_with_text_offer_the_reader_and_the_rest_do_not(client: Client, ingested):
    """Half the list can be read as text; the page must say which half (`DOCUMENTS_READER_LINK_PRD` D1).

    The four forms have no ingested text, and D2 says they gain **nothing** — not a
    disabled control and not a chip — because a form is published as a file and that is
    the whole truth about it.
    """
    html = client.get("/documents/").content.decode()

    for code in WITH_TEXT:
        assert f'href="/documents/{code}/read/"' in html, f"{code} has text but no reader link"
        assert "Read the text" in html

    for spec in DOCUMENTS:
        if spec.code in WITH_TEXT:
            continue
        assert f'href="/documents/{spec.code}/read/"' not in html, (
            f"{spec.code} has no ingested text, so it must not offer the reader"
        )


def test_no_row_links_to_a_reader_that_would_apologise(client: Client, ingested):
    """A link the page prints must open the document's text, not "we have not published it".

    That page is honest, but a row that links to it promises something the group cannot
    show. This is the assertion that would have caught `corpus_for()` answering for a
    document whose text was never ingested.
    """
    html = client.get("/documents/").content.decode()

    for code in WITH_TEXT:
        response = client.get(f"/documents/{code}/read/")
        assert response.status_code == 200, f"{code}'s reader link does not resolve"
        assert b"not published the text" not in response.content, (
            f"{code} links to a reader that has no text"
        )


def test_the_page_does_not_query_once_per_row(client: Client, ingested, django_assert_num_queries):
    """Eight rows, and the page already made one query for the list.

    A `corpus_for()` per row would add eight more — the shape that turns a light public
    page into a N+1 the day a ninth document is published. The ingested set is resolved
    once and matched in Python.
    """
    with django_assert_num_queries(2):
        client.get("/documents/")


def test_the_home_band_offers_the_same_reader_link(client: Client, ingested):
    """One list, rendered on two pages, so both must show the same verbs.

    The band and `/documents/` share `_doc_rows.html` on purpose: two hand-maintained
    lists disagreed about which documents exist once already (C2).
    """
    html = client.get("/").content.decode()

    for code in WITH_TEXT:
        assert f'href="/documents/{code}/read/"' in html, f"home does not link {code}'s text"
