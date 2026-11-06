"""The public self-check's form — validation at the boundary, rules in the service.

Thin in the way `build_principles.md` §II asks: the field set is **built from the controls** the
service resolved, so a question cannot exist in the template and not in the form (or the other way
round), and the choices are the reviewed answer sets rather than strings a template retyped.

Two things here are not ordinary form work:

- **The upper limit is a paranoia field, not a question.** `website` is off-screen and must stay
  empty; a submission that fills it is a bot. The form does not raise — telling a bot which field
  caught it is a favour — so the view simply treats it as *no consent*, renders the result, and
  writes nothing (`SELF_CHECK_PRD` §4.4).
- **E1 and E2 never become `BooleanField`s in the loop.** They are consent *texts* with an act
  beside them, and the wording is data (`ConsentText`) that has to be shown in full. The two
  checkboxes are named for the acts (`research_consent`, `demographic_consent`) and the template
  pairs each with its text — never with a label that claims more than the text says.
"""

from __future__ import annotations

from typing import Any

from django import forms

from core.services._selfcheck import (
    CENSUS_AGE_BAND,
    CENSUS_DEMOGRAPHIC_GROUP,
    CENSUS_GENDER,
    GROUPS,
    Control,
    Group,
    SelfCheckForm,
    build_check,
)


def _choices(options) -> list[tuple[str, str]]:
    return [(option.code, option.label) for option in options]


class SelfCheckAnswersForm(forms.Form):
    """Twenty controls, two consents, one optional note, one honeypot.

    In:  `data` — the POST; `check` — the resolved question set (the view already has it, so the
         page and the validation cannot disagree about what was asked).
    Out: a bound form whose `cleaned_data` the service consumes.
    Side Effects: none. No form here writes a model.
    """

    exit_note = forms.CharField(
        max_length=280,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "maxlength": "280"}),
    )
    research_consent = forms.BooleanField(required=False)
    demographic_consent = forms.BooleanField(required=False)
    consent_version = forms.CharField(required=False, widget=forms.HiddenInput)
    census_gender = forms.ChoiceField(
        required=False, choices=[("", "—")] + [(value, value) for value in CENSUS_GENDER]
    )
    census_age_band = forms.ChoiceField(
        required=False, choices=[("", "—")] + [(value, value) for value in CENSUS_AGE_BAND]
    )
    census_demographic_group = forms.ChoiceField(
        required=False,
        choices=[("", "—")] + [(value, value) for value in CENSUS_DEMOGRAPHIC_GROUP],
    )
    #: The honeypot. `required=False` and never validated with a message: see the module docstring.
    #: A **text** input (not `HiddenInput`) because a hidden field is what a bot's form-filler skips,
    #: and an off-screen field a person never reaches is the point.
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    def __init__(self, *args, check: SelfCheckForm | None = None, category: str = "CROPS", **kwargs):
        self.check = check or build_check(category)
        super().__init__(*args, **kwargs)
        for control in self.check.controls:
            if control.kind == "CONSENT":
                # The act, not the wording: the text is `ConsentText` and is rendered beside this.
                continue
            if control.kind == "MULTI":
                self.fields[control.key] = forms.MultipleChoiceField(
                    required=False,
                    choices=_choices(control.options),
                    widget=forms.CheckboxSelectMultiple,
                )
            else:
                # `RadioSelect`, not the default `Select`: the template renders one chip per option
                # (`{{ choice.tag }}` + `{{ choice.choice_label }}`), and a `Select` yields a single
                # subwidget holding the whole `<select>` — which silently renders **nothing** when
                # iterated. That defect passed every Django test and was caught in the browser
                # (`tests/e2e/test_selfcheck_wizard.py`), because a form with no inputs still
                # submits, still validates (every field optional) and still renders a result.
                self.fields[control.key] = forms.ChoiceField(
                    required=False,
                    choices=_choices(control.options),
                    widget=forms.RadioSelect,
                )
        if self.check.research_consent is not None:
            self.fields["consent_version"].initial = self.check.research_version

    # --- What the template iterates, already paired ---------------------------------------

    @property
    def groups(self) -> tuple[tuple[Group, tuple[tuple[Control, Any], ...]], ...]:
        """Each group with its controls paired to their bound fields — no `form[key]` in a template."""
        return tuple(
            (
                group,
                tuple(
                    (control, self[control.key])
                    for control in group.controls
                    if control.kind != "CONSENT" and control.key in self.fields
                ),
            )
            for group in self.check.groups
        )

    @property
    def consent_rows(self) -> tuple[tuple[Control, Any, Any], ...]:
        """`(control, consent text, bound field)` for E1 and E2, in the order the ledger has them."""
        pairs = (
            ("E1", self.check.research_consent, "research_consent"),
            ("E2", self.check.demographic_consent, "demographic_consent"),
        )
        controls = {control.key: control for control in self.check.controls}
        return tuple(
            (controls[key], text, self[field_name])
            for key, text, field_name in pairs
            if key in controls
        )

    @property
    def is_bot(self) -> bool:
        """True when the honeypot was filled. The view's only use for it is "do not store"."""
        return bool((self.data.get("website") or "").strip())

    @property
    def start_step(self) -> int:
        """Which wizard step to reopen on: the first group with an error, else 1.

        The steps are client-side (`SELF_CHECK_PRD` §11.5), so a server-side error has to say where
        it was — otherwise a visitor is returned to step 1 and told nothing about why.
        """
        order = [key for key, _title, _lede in GROUPS]
        for key in self.errors:
            control = next((c for c in self.check.controls if c.key == key), None)
            if control is not None and control.group in order:
                return order.index(control.group) + 1
        if self.non_field_errors() or "research_consent" in self.errors or (
            "demographic_consent" in self.errors
        ):
            return 5
        return 1
