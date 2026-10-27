"""/documents/ — the documents page, and the download it links to.

Thin views (`build_principles.md` §II): the index parses nothing and renders one
context; the download resolves one published row and streams one file. Every string
on the index comes from `core.services._documents.DOCUMENTS` through the database,
so the home page's band and this page cannot disagree about which documents exist.

**Why the files are streamed instead of served from `/media/`.** Three reasons, all
of them failures this project has already had:

* `is_published` has to be consulted per request. A static file at a guessable path
  cannot consult anything, and D22's dossiers are one careless `collectstatic` away
  from being public.
* `DEBUG=True` serves `MEDIA_ROOT` straight to the browser, so a document taken down
  in the admin would stay downloadable from the URL someone bookmarked.
* The public address must be `/documents/<code>/`, because `content_inventory.md` §4
  makes the WordPress cutover a redirect table. A `/media/public/documents/opp.pdf`
  URL can be redirected too, but not to a *code* the group can rename.

A published document whose file is missing is **503, not 404** (§VII.5). A 404 would
state that the document does not exist, which is false — the home page links to it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render

from core.models import PublicDocument
from core.services._documents import absolute_path, documents_context, reader_for
from core.services._public import Page, chrome_context, public_context

logger = logging.getLogger(__name__)


def documents(request):
    """The list. Every published row, in the order the seed declares."""
    return render(
        request, "public/documents.html", public_context("documents") | documents_context()
    )


def document_file(request, code: str):
    """Stream one published document. Unpublished and unknown codes are the same 404."""
    document = get_object_or_404(PublicDocument.objects.published(), code=code)
    path = absolute_path(document)

    if not path.is_file():
        # Not a 404: the row is published, so the document is meant to be here. Log it
        # with enough context to finish the diagnosis from the log alone.
        logger.error(
            "published document missing from the deployment",
            extra={
                "document_code": document.code,
                "expected_path": str(path),
                "source_path": document.source_path,
            },
        )
        return HttpResponse(
            "This document is listed on our site but is missing from this deployment. "
            "Please contact the administrator.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    response = FileResponse(
        Path(path).open("rb"),
        content_type=document.content_type,
        as_attachment=True,
        filename=document.download_name,
    )
    return response


def document_reader(request, code: str):
    """The concordance: the document's structure as navigation, one branch open.

    Unpublished and unknown codes are the same 404, for the same reason the download is:
    `is_published` is the only gate, and a citation is not an exception to it.
    """
    document = get_object_or_404(PublicDocument.objects.published(), code=code)
    reader = reader_for(
        document,
        request.GET.get("q", ""),
        request.GET.get("section", ""),
    )
    page = Page(
        key="document-reader",
        title=reader.title,
        description=(
            f"{reader.document.title}, as we ingested it — the branch a citation names, "
            "with the passages it quotes."
        ),
        eyebrow="The documents",
        heading=document.title,
        lede=(
            "The standard's own structure, section by section, as we ingested it. Choose a "
            "section, search the whole document, or follow a citation straight to the line "
            "it quotes."
        ),
    )
    return render(
        request,
        "public/document_reader.html",
        chrome_context(page)
        | {
            "reader": reader,
            "canonical": request.build_absolute_uri(reader.canonical_path),
        },
    )
