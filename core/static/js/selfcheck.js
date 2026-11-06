/*
 * selfcheck.js — the public self-check's stepped shape (`SELF_CHECK_PRD` §11.5).
 *
 * This file is **navigation only**, and that is the rule that keeps the page honest: not one
 * answer is validated, gated or scored here. §11.5 is explicit that "a step can be left unanswered
 * — the check is not a demand", so the only thing `Next` does is scroll the visitor forward. The
 * server decides everything else, and every sentence the visitor reads comes from a service.
 *
 * Four behaviours, each removable without breaking the page:
 *
 *   1. `data-selfcheck-js` on <html> turns the stacked sections into steps. Without this file the
 *      browser shows all five sections and the one submit button at the end — the no-JavaScript
 *      shape, which is the shape a farm connection on a tired phone gets.
 *   2. The numbered nav is a position indicator: clicking a *visited or next* step moves there, and
 *      the "what it means" button only unlocks after a submit (there is nothing to show before it).
 *   3. The answered count per step is a courtesy, not a completeness bar.
 *   4. The census consent (E2) is refused without the research consent (E1) — §11.5's "intra-step
 *      dependency". This is the **UI** of a rule the server also enforces; the server test is what
 *      makes it true, and this only spares a visitor a round trip.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var form = document.querySelector(".wiz__form");
  if (!form) return;

  root.setAttribute("data-selfcheck-js", "on");

  var steps = Array.prototype.slice.call(document.querySelectorAll(".wiz__step"));
  if (!steps.length) return;

  var navButtons = Array.prototype.slice.call(
    document.querySelectorAll(".wiz__nav [data-goto]")
  );
  var titles = steps.map(function (step) {
    var heading = step.querySelector(".wiz__h2");
    return heading ? heading.textContent.trim() : "";
  });
  var countLabel = document.getElementById("wiz-count");
  var current = Number(document.querySelector(".wiz").getAttribute("data-start")) || 1;
  if (current < 1 || current > steps.length) current = 1;

  function stepOf(index) {
    return steps[index - 1];
  }

  function answered(index) {
    var step = stepOf(index);
    if (!step) return { done: 0, total: 0 };
    var names = {};
    Array.prototype.forEach.call(step.querySelectorAll("input, textarea"), function (input) {
      // Consents are not progress and the honeypot is not a question.
      if (input.type === "hidden" || input.name === "website") return;
      names[input.name] = true;
    });
    var ids = Object.keys(names);
    var done = ids.filter(function (name) {
      var inputs = form.querySelectorAll('[name="' + name + '"]');
      return Array.prototype.some.call(inputs, function (input) {
        return input.type === "checkbox" || input.type === "radio" ? input.checked : !!input.value;
      });
    }).length;
    return { done: done, total: ids.length };
  }

  function paintNav() {
    navButtons.forEach(function (button) {
      var to = Number(button.getAttribute("data-goto"));
      button.removeAttribute("aria-current");
      if (to === current) button.setAttribute("aria-current", "step");
      if (to <= steps.length) {
        var progress = answered(to);
        button.setAttribute(
          "data-done",
          progress.total > 0 && progress.done === progress.total ? "true" : "false"
        );
      }
    });
    if (countLabel) {
      countLabel.textContent =
        "Step " + current + " of " + steps.length + " · " + (titles[current - 1] || "");
    }
  }

  function paintCounter() {
    var counter = stepOf(current) && stepOf(current).querySelector("[data-counter]");
    if (!counter) return;
    var progress = answered(current);
    counter.textContent = progress.done + " of " + progress.total + " answered";
  }

  function go(to, focus) {
    if (to < 1 || to > steps.length) return;
    steps.forEach(function (step, index) {
      var active = index + 1 === to;
      step.toggleAttribute("data-current", active);
      if (!active) step.setAttribute("hidden", "");
      else step.removeAttribute("hidden");
    });
    current = to;
    paintNav();
    paintCounter();
    window.scrollTo(0, 0);
    // Only move focus when a person moved: focusing on the first paint puts a focus ring around a
    // heading nobody touched, which looks like a validation error and is announced as one.
    var heading = stepOf(to).querySelector(".wiz__h2");
    if (focus && heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
  }

  document.addEventListener("click", function (event) {
    var next = event.target.closest("[data-next]");
    var back = event.target.closest("[data-back]");
    var goto = event.target.closest("[data-goto]");
    if (next) return go(current + 1, true);
    if (back) return go(current - 1, true);
    if (goto && !goto.disabled) return go(Number(goto.getAttribute("data-goto")), true);
  });

  form.addEventListener("change", function (event) {
    if (event.target && event.target.name === "research_consent") {
      var census = form.querySelector('[data-consent="E2"]');
      if (census) {
        var box = census.querySelector('input[name="demographic_consent"]');
        var fields = census.querySelectorAll(".field-grid select, .field-grid input, .field-grid textarea");
        if (box) {
          box.disabled = !event.target.checked;
          if (!event.target.checked) box.checked = false;
        }
        Array.prototype.forEach.call(fields, function (field) {
          field.disabled = !event.target.checked;
        });
      }
    }
    paintNav();
    paintCounter();
  });

  document.addEventListener("keydown", function (event) {
    var target = event.target;
    if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
    if (event.key === "ArrowRight" && current < steps.length) {
      event.preventDefault();
      go(current + 1, true);
    }
    if (event.key === "ArrowLeft" && current > 1) {
      event.preventDefault();
      go(current - 1, true);
    }
  });

  // Start on the step the server named — 5 when a consent was refused, 1 otherwise.
  go(current);

  // The census consent starts refused (§11.5), and stays refused through a re-render.
  var research = form.querySelector('input[name="research_consent"]');
  if (research) form.dispatchEvent(new Event("change", { bubbles: true }));
  if (research) {
    var census = form.querySelector('[data-consent="E2"]');
    if (census && research.checked) {
      var box = census.querySelector('input[name="demographic_consent"]');
      if (box) box.disabled = false;
    }
  }
})();
