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
