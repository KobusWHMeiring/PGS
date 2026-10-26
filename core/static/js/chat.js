/*
 * chat.js — the only hand-written JavaScript on the public site, and deliberately
 * tiny. HTMX does the exchange; this file does four things it does not:
 *
 *   1. append the visitor's message and clear the box as soon as the request
 *      starts, so the turn appears immediately rather than after the answer;
 *   2. keep the newest message in view after a swap;
 *   3. let Enter send and Shift+Enter insert a newline;
 *   4. let a 429 or 503 swap its explanation into the thread. HTMX ignores non-2xx
 *      responses by default, which would leave the visitor staring at a page that
 *      silently did nothing;
 *   5. copy an answer page's citation, and do nothing at all when the Clipboard API is
 *      unavailable — the citation is already selectable text, so a broken button is
 *      worse than no button.
 *
 * No build step, no module loader, no framework (build_principles.md §IV). If this
 * file fails to load, the form still posts and the server still renders a full page.
 */
(function () {
  "use strict";

  // Optimistic turn state. `sending` stops a second submit while the first is in
  // flight; `pendingRow` is the bubble we added, kept so a failed request can remove
  // it; `restoreText` puts the question back after a rate-limit rejection.
  var sending = false;
  var pendingText = "";
  var pendingRow = null;
  var restoreText = "";

  function thread() {
    return document.getElementById("chat-thread");
  }

  function appendPendingUserMessage(text) {
    var node = thread();
    if (!node) {
      return;
    }
    var empty = node.querySelector(".chat__empty");
    if (empty) {
      empty.remove();
    }
    var row = document.createElement("div");
    row.className = "chat__row chat__row--user";
    var bubble = document.createElement("p");
    bubble.className = "chat__bubble chat__bubble--user";
    bubble.textContent = text;
    row.appendChild(bubble);
    node.appendChild(row);
    pendingRow = row;
    scrollToLatest(true);
  }

  function scrollToLatest(bringIntoView) {
    var node = thread();
    if (!node) {
      return;
    }
    var rows = node.querySelectorAll(".chat__row");
    if (!rows.length) {
      node.scrollTop = 0;
      return;
    }
    // Scroll to the *start* of the newest row, not the bottom of the thread. An
    // answer can be longer than the window; showing its last line first hides the
    // sentence that answers the question. The reader can scroll from the top.
    var last = rows[rows.length - 1];
    var delta = last.getBoundingClientRect().top - node.getBoundingClientRect().top;
    node.scrollTop = node.scrollTop + delta - 8;

    if (bringIntoView) {
      var box = node.getBoundingClientRect();
      if (box.top < 0 || box.bottom > window.innerHeight) {
        // On a phone the form is below the thread, so after submitting the answer is
        // above the viewport. Bring the thread back to the top of the screen; the
        // form remains one scroll below, exactly where it was.
        node.scrollIntoView({ block: "start" });
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    scrollToLatest(false);
  });

  /*
   * Enter sends; Shift+Enter keeps a newline. A textarea inserts a newline on Enter
   * by default, which is the wrong default for a one-question box. The click goes
   * through the same path as the Ask button, so the browser's required-field
   * validation and HTMX's submit interception still apply. `isComposing` (and the
   * legacy keyCode 229) guard IME input: while a composed character is being built,
   * Enter belongs to the input method, not to the form.
   */
  document.body.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    if (event.isComposing || event.keyCode === 229) {
      return;
    }
    var input = event.target;
    if (!input || input.id !== "id_question") {
      return;
    }
    var form = input.closest(".chat-form");
    var send = document.getElementById("chat-send");
    if (!form || !send) {
      return;
    }
    event.preventDefault();
    if (send.classList.contains("htmx-request")) {
      return; // a question is already in flight; do not create a duplicate turn
    }
    send.click();
  });

  document.body.addEventListener("htmx:beforeRequest", function (event) {
    var elt = event.detail.elt;
    if (!elt || !elt.classList || !elt.classList.contains("chat-form")) {
      return;
    }
    if (sending) {
      event.preventDefault();
      return;
    }
    var input = document.getElementById("id_question");
    if (!input) {
      return;
    }
    var text = input.value.trim();
    if (!text) {
      return;
    }
    // HTMX has already serialised the form by now, so clearing cannot empty the POST.
    sending = true;
    pendingText = text;
    appendPendingUserMessage(text);
    input.value = "";
  });

  document.body.addEventListener("htmx:afterRequest", function () {
    sending = false;
  });

  document.body.addEventListener("htmx:beforeSwap", function (event) {
    var status = event.detail.xhr.status;
    if (status === 429) {
      // The rate limiter rejects before the question is stored, so the server thread
      // will not contain it. Put the text back after the swap instead of losing it.
      restoreText = pendingText;
    }
    if (status === 429 || status === 503) {
      // The body is already the thread fragment the server rendered. Swap it, but
      // do not let HTMX treat it as an unhandled error: the message is the point.
      event.detail.shouldSwap = true;
      event.detail.isError = false;
    }
  });

  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (!event.detail.target || event.detail.target.id !== "chat-thread") {
      return;
    }
    var input = document.getElementById("id_question");
    if (input) {
      // Do not reset the form here: the visitor may have started the next question
      // while this one was in flight, and the response must not delete it.
      if (restoreText && !input.value) {
        input.value = restoreText;
      }
      input.focus({ preventScroll: true });
    }
    restoreText = "";
    pendingText = "";
    pendingRow = null;
    scrollToLatest(true);
  });

  document.body.addEventListener("htmx:responseError", function (event) {
    // A network-level failure has no server-rendered fragment. Say so in the thread
    // rather than leaving the previous answer as the last word.
    if (event.detail.xhr.status === 0) {
      // The request never reached the server. Remove the optimistic bubble (it would
      // read as sent) and put the question back so the visitor can retry it.
      if (pendingRow && pendingRow.parentNode) {
        pendingRow.parentNode.removeChild(pendingRow);
      }
      pendingRow = null;
      var input = document.getElementById("id_question");
      if (input && pendingText && !input.value) {
        input.value = pendingText;
        input.focus({ preventScroll: true });
      }
      pendingText = "";
      var node = thread();
      if (node) {
        var notice = document.createElement("div");
        notice.className = "chat__row";
        var bubble = document.createElement("div");
        bubble.className = "chat__bubble chat__bubble--refusal";
        bubble.setAttribute("role", "alert");
        bubble.textContent =
          "The question could not be sent. Please check your connection and try again.";
        notice.appendChild(bubble);
        node.appendChild(notice);
        scrollToLatest();
      }
    }
  });

  // --- Copy the citation (answer pages) -------------------------------------
  //
  // Progressive enhancement only: the citation is a normal, selectable paragraph and this
  // button is a convenience. When `navigator.clipboard` is missing (an older browser, a
  // non-secure origin), the handler returns silently rather than falling back to
  // `execCommand` or an alert — a button that reports failure on a farm phone is worse
  // than a button that is simply inert.
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-copy-target]");
    if (!button || !navigator.clipboard || !navigator.clipboard.writeText) {
      return;
    }
    var source = document.querySelector(button.getAttribute("data-copy-target"));
    if (!source) {
      return;
    }
    var label = button.getAttribute("data-copy-label") || button.textContent;
    navigator.clipboard.writeText(source.textContent.trim()).then(
      function () {
        button.textContent = "Copied";
        window.setTimeout(function () {
          button.textContent = label;
        }, 2000);
      },
      function () {
        /* Refused permission: leave the button alone. The text is still selectable. */
      }
    );
  });
})();
