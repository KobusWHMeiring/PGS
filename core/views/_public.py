"""The public pages — home, the three "who we are" pages, joining, and contact.

Thin views (`build_principles.md` §II): parse nothing, call one service, render.
Every string, figure and route a template needs comes from
`core.services._public.public_context`, so a page cannot disagree with another page
about the membership fee, and no template holds business logic.

MVP 0 ships these as public preview pages (D21) — the registry, farm status and
certificates are MVP 2 and are deliberately absent (DESIGN §1, `MVP0_PRD` §3).
"""

from __future__ import annotations

from django.shortcuts import render

from core.services._board import board_context
from core.services._documents import documents_context
from core.services._public import public_context


def home(request):
    # The home page carries the documents band, so it needs the same list the
    # documents page renders — from one service, in the order the seed declares.
    return render(request, "public/home.html", public_context("home") | documents_context())


def organics(request):
    return render(request, "public/organics.html", public_context("organics"))


def how_it_works(request):
    return render(request, "public/how_it_works.html", public_context("how_it_works"))


def members(request):
    return render(request, "public/members.html", public_context("members"))


def become_a_member(request):
    return render(request, "public/become_a_member.html", public_context("become_a_member"))


def building(request):
    # The board is a generated artefact (`core/services/_board_data.py`), not a query and not
    # a read of `product/backlog/`: this view touches no database, so a PRD edit cannot change
    # the public site between deploys (D74b).
    return render(request, "public/building.html", public_context("building") | board_context())


def contact(request):
    return render(request, "public/contact.html", public_context("contact"))
