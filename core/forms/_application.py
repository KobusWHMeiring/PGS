"""The application flow's forms — validation at the boundary, rules in the services.

Every form here is thin in the way `build_principles.md` §II asks: it parses and
validates what a person typed, then hands the act to exactly one service. No form
computes a band, a status or a fee, and no form writes a model directly.

The one rule worth reading twice is `AccountForm`: **it cannot create an account
without the Q8 consent**, and it carries the consent *version* it rendered in a hidden
field. If the group publishes new wording while a farmer has the page open, the service
refuses the older version rather than recording agreement to text that person did not
read — a consent record that names the wrong wording is worse than no record, because it
looks like evidence.
"""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from core.models import Category, Member, Pledge
from core.services._application import ApplicantDetails, create_application
from core.services._membership import record_pledge

#: The two branches OPP §I.1 prints as an OR. One or the other, never both (A3 refuses
#: the row that has both), so the form offers them as a choice rather than as two
#: independent checkboxes the farmer has to reason about.
BRANCH_LAND_HISTORY = "land_history"
BRANCH_IN_CONVERSION = "in_conversion"


class AccountForm(forms.Form):
    """The account step: Q7's seven fields, a password, and the Q8 consent."""

    first_name = forms.CharField(
        max_length=150, label="First name", widget=forms.TextInput(attrs={"autocomplete": "given-name"})
    )
    last_name = forms.CharField(
        max_length=150, label="Last name", widget=forms.TextInput(attrs={"autocomplete": "family-name"})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "inputmode": "email"}),
        help_text="This is also how you sign in. Verification is not available yet.",
    )
    phone = forms.CharField(
        max_length=32,
        label="Phone",
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
    )
    farm_name = forms.CharField(
        max_length=200,
        label="Farm name",
        widget=forms.TextInput(attrs={"autocomplete": "organization"}),
        help_text="As you would write it. The administrator can add other spellings later.",
    )
    nearest_town = forms.CharField(
        max_length=120,
        label="Nearest town",
        widget=forms.TextInput(attrs={"autocomplete": "address-level2"}),
        help_text="How the group describes where you are — not a postal address.",
    )
    contact_name = forms.CharField(
        max_length=200,
        label="Who should the group speak to about a visit?",
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    password1 = forms.CharField(
        label="Choose a password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Repeat the password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    consent = forms.BooleanField(
        required=False,  # the *service* refuses; a field-level "required" would only say "tick me"
        label="May we keep these details?",
    )
    consent_version = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean(self):
        data = super().clean()
        password = data.get("password1")
        if password and password != data.get("password2"):
            self.add_error("password2", "The two passwords do not match.")
        elif password:
            # Django's own validators (length, common, numeric, similarity): the same
            # rules the rest of the project uses, not a second, weaker set.
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return data

    def to_details(self) -> ApplicantDetails:
        """The seven Q7 fields as the service's frozen record."""
        return ApplicantDetails(
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data["email"],
            phone=self.cleaned_data["phone"],
            farm_name=self.cleaned_data["farm_name"],
            nearest_town=self.cleaned_data["nearest_town"],
            contact_name=self.cleaned_data["contact_name"],
        )

    def create(self) -> Member:
        """Hand the act to the service, with the version this form actually rendered."""
        return create_application(
            self.to_details(),
            password=self.cleaned_data["password1"],
            consent_version=self.cleaned_data["consent_version"],
            consent_given=bool(self.cleaned_data["consent"]),
        )


class PledgeForm(forms.Form):
    """The farmer pledge, as OPP §I.1 prints it — including the OR.

    The wording is in the template, because it is what the member reads and signs; this
    form collects the answers. A3 refuses combinations the printed form cannot hold, so
    the view renders that refusal as a form error instead of a 500.
    """

    method = forms.ChoiceField(
        label="How is the pledge being made?",
        choices=Pledge.Method.choices,
        initial=Pledge.Method.SIGNATURE,
        widget=forms.RadioSelect,
        help_text="A verbal pledge or a distinctive mark is a real pledge — it needs a witness and a record.",
    )
    place = forms.CharField(max_length=120, label="Place")
    witness_name = forms.CharField(max_length=200, label="Witness's name", required=False)
    witness_designation = forms.CharField(
        max_length=120, label="Witness's designation", required=False
    )
    evidence_document = forms.FileField(
        label="Photograph or other record of the pledge",
        required=False,
        help_text="Required for a verbal pledge (OPP §I.2): the record is what makes it evidence.",
    )
    branch = forms.ChoiceField(
        label="Which applies to your land?",
        choices=(
            (BRANCH_LAND_HISTORY, "The land history below is true for all the land I am applying for"),
            (BRANCH_IN_CONVERSION, "I/We have applied for In-Conversion status"),
        ),
        initial=BRANCH_LAND_HISTORY,
        widget=forms.RadioSelect,
    )
    annual_months = forms.IntegerField(
        min_value=0, max_value=120, required=False, label="Annual production — months clear"
    )
    pasture_months = forms.IntegerField(
        min_value=0, max_value=120, required=False, label="Pastures and meadows — months clear"
    )
    perennial_months = forms.IntegerField(
        min_value=0, max_value=120, required=False, label="Other perennials — months before harvest"
    )
    in_conversion_months = forms.TypedChoiceField(
        label="In-conversion period",
        choices=((12, "12 months"), (18, "18 months")),
        coerce=int,
        required=False,
        empty_value=None,
    )

    def record(self, member: Member) -> Pledge:
        """Hand the act to A3's `record_pledge`, which computes `land_history_conflict`."""
        data = self.cleaned_data
        in_conversion = data["branch"] == BRANCH_IN_CONVERSION
        return record_pledge(
            member,
            kind=Pledge.Kind.FARMER,
            method=data["method"],
            place=data["place"],
            in_conversion_declared=in_conversion,
            in_conversion_months=data["in_conversion_months"] if in_conversion else None,
            declared_annual_clear_months=None if in_conversion else data["annual_months"],
            declared_pasture_clear_months=None if in_conversion else data["pasture_months"],
            declared_perennial_clear_months=None if in_conversion else data["perennial_months"],
            witness_name=data["witness_name"],
            witness_designation=data["witness_designation"],
            evidence_document=data["evidence_document"],
        )


class CategoriesForm(forms.Form):
    """The categories sought (FORM A) — a tick here *is* the application (D36)."""

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="What do you want assessed?",
        error_messages={
            "required": "Tick at least one category: a tick is what makes this an application.",
        },
    )

    def __init__(self, *args, farm=None, **kwargs):
        super().__init__(*args, **kwargs)
        if farm is not None and not self.is_bound:
            # An application resumed, or a step revisited: show what is already applied for.
            self.fields["categories"].initial = farm.categories.values_list(
                "category_id", flat=True
            )


class TurnoverForm(forms.Form):
    """The annual turnover the fee is based on, in Rand as the farmer knows it.

    Integer Rand in, integer cents out — a float never touches money (§III). The band is
    **not** on this form: the farmer declares a turnover and the seeded OPP §2.3 scale
    decides the band, so a farmer cannot choose a cheaper band than their own figure.
    """

    turnover_rands = forms.IntegerField(
        min_value=0,
        label="Annual turnover (Rand)",
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "step": 1000}),
        help_text="Your best figure for a normal year, before the visit. It is peer-reviewed, not audited here.",
    )

    def cents(self) -> int:
        return self.cleaned_data["turnover_rands"] * 100


class SignInForm(AuthenticationForm):
    """The way back in: the address is the username, so the label says so.

    Django's default label is "Username", which is the one word a farmer does not have —
    the account step collected an email address and nothing else. The field is still
    `username` because that is the model's column, and 1a has no mail provider (D84) to
    offer a reset link the portal cannot send.
    """

    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
