"""The chat form — one field, and a length cap that matches the service.

The cap lives in two places on purpose: the form refuses an over-long question with a
Django validation message before any service call, and `validate_question()` refuses
it again at the service boundary. The second is not redundant — a management command,
a future API caller or a test can reach the service without the form. The constant is
imported from the service so the two cannot drift.
"""

from __future__ import annotations

from django import forms

from core.services._chatbot import MAX_QUESTION_CHARS


class QuestionForm(forms.Form):
    """Ask one question.

    `strip=True` means a question of spaces is required-empty rather than sent to
    Gemini, which rejects empty content. `autocomplete="off"` avoids a browser
    suggesting a previously typed personal question across a shared device.
    """

    question = forms.CharField(
        max_length=MAX_QUESTION_CHARS,
        strip=True,
        label="Your question",
        error_messages={
            "required": "Please type a question.",
            "max_length": (
                f"Please keep the question to {MAX_QUESTION_CHARS} characters or fewer."
            ),
        },
        widget=forms.Textarea(
            attrs={
                "class": "chat-form__input",
                "rows": 3,
                "maxlength": MAX_QUESTION_CHARS,
                "placeholder": "Ask about the standard, our procedures or the certification landscape…",
                "aria-label": "Your question",
                "autocomplete": "off",
                "spellcheck": "true",
            }
        ),
    )

    #: The consent control (D64). Unticked is the honest default — silence is not consent —
    #: and the help text is the console's promise, so it ships with the control rather than in
    #: a separate copy edit: the card lands as *awaiting review* precisely because this says an
    #: administrator reads it first.
    publish = forms.BooleanField(
        required=False,
        label="Add this question to the public questions database",
        help_text=(
            "Other visitors will see the question and the answer, without your name. "
            "Don't include anyone else's name or farm. An administrator reads it before "
            "it appears."
        ),
        widget=forms.CheckboxInput(attrs={"class": "chat-form__checkbox"}),
    )
