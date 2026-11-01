/*
 * reader-grid.js — column sizing and resizing for the reader's `layout: grid` tables (D77).
 *
 * The seals comparison is a spreadsheet: five columns of the same weight, and a reader comparing
 * them wants to give one column more room. This file does four things, and **none of them is
 * required to read the table**:
 *
 *   1. measure the columns the browser laid out and freeze them as pixel widths, so a drag can
 *      move one column without the browser re-flowing the others;
 *   2. let a pointer drag a header edge, and let the keyboard move it too (arrow keys, ±8 px;
 *      Shift for ±24; Home to reset). The handle is a `role="separator"` in the template, and a
 *      keyboard user must be able to do what a pointer user can;
 *   3. remember the widths per document and table (`pgs.reader.<doc_key>.<anchor>`), so a reader
 *      who widens the Fee column once does not do it again on the next visit;
 *   4. add the two controls — Compact, Reset — and a disclosure of nothing else. A control that
 *      does not work is worse than no control, so the toolbar is built here rather than rendered
 *      in the template: no JavaScript, no dead buttons.
 *
 * No build step, no module loader, no framework (build_principles.md §IV). If this file fails to
 * load, the table is the one the CSS already draws, at the browser's own column widths.
 */
(function () {
  "use strict";

  //: The narrowest a column may be dragged, and the widest. In px, and multiples of 8 so a
  //: keyboard user's arrows land on the same grid the pointer does.
  var MIN_WIDTH = 96;
  var MAX_WIDTH = 720;
  var ARROW_STEP = 8;
  var SHIFT_STEP = 24;

  function storageKey(table) {
    return "pgs.reader." + (table.getAttribute("data-grid-key") || "table");
  }

  function read(key) {
    try {
      return JSON.parse(window.localStorage.getItem(key) || "null");
    } catch (error) {
      // A blocked or full store is not an error worth failing the page for: the table reads
      // without persistence, and that is the whole requirement.
      return null;
    }
  }

  function write(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      /* see read() */
    }
  }

  function columns(table) {
    return Array.prototype.slice.call(table.querySelectorAll("colgroup col"));
  }

  function headerCells(table) {
    return Array.prototype.slice.call(table.querySelectorAll("thead th"));
  }

  function widths(table) {
    return columns(table).map(function (col) {
      return Math.round(col.getBoundingClientRect().width);
    });
  }

  function setWidths(table, values) {
    var cols = columns(table);
    values.forEach(function (value, index) {
      if (cols[index]) {
        cols[index].style.width = value + "px";
      }
    });
    table.setAttribute("data-resizable", "");
  }

  //: Measure what fits, then take the difference off the widest column. A collapsed-border table
  //: lays out a few pixels wider than the sum of its columns, and `table-layout: fixed` then makes
  //: the wrapper scroll by that difference — a sideways scroll the grid does not need and the
  //: reader did not ask for. Two pixels of correction is invisible; a scrollbar is not.
  function apply(table, values) {
    var widths = values.slice();
    setWidths(table, widths);
    var wrap = table.closest(".reader__grid-wrap");
    if (wrap && wrap.clientWidth) {
      var excess = wrap.scrollWidth - wrap.clientWidth;
      if (excess > 0) {
        var widest = 0;
        for (var index = 1; index < widths.length; index += 1) {
          if (widths[index] > widths[widest]) {
            widest = index;
          }
        }
        widths[widest] = Math.max(MIN_WIDTH, widths[widest] - excess);
        setWidths(table, widths);
      }
    }
    syncSeparators(table, widths);
    return widths;
  }

  function syncSeparators(table, values) {
    headerCells(table).forEach(function (cell, index) {
      var handle = cell.querySelector(".reader__grid-resizer");
      if (!handle) {
        return;
      }
      var width = values[index] === undefined ? 0 : values[index];
      handle.setAttribute("aria-valuemin", String(MIN_WIDTH));
      handle.setAttribute("aria-valuemax", String(MAX_WIDTH));
      handle.setAttribute("aria-valuenow", String(width));
      // The separator belongs to the boundary *after* its own column, which is the one it moves.
      handle.setAttribute(
        "aria-valuetext",
        width ? width + " pixels" : ""
      );
    });
  }

  function resize(table, index, value) {
    var values = widths(table);
    values[index] = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, Math.round(value)));
    // Freeze every column first, so the one being dragged grows against fixed neighbours rather
    // than against the browser's own idea of how wide the others should be.
    write(storageKey(table), { widths: apply(table, values) });
  }

  function reset(table) {
    columns(table).forEach(function (col) {
      col.style.width = "";
    });
    table.removeAttribute("data-resizable");
    try {
      window.localStorage.removeItem(storageKey(table));
    } catch (error) {
      /* see read() */
    }
  }

  function setCompact(table, on) {
    if (on) {
      table.setAttribute("data-compact", "");
    } else {
      table.removeAttribute("data-compact");
    }
    var state = read(storageKey(table)) || {};
    state.compact = !!on;
    write(storageKey(table), state);
  }

  function buildTools(table) {
    var wrap = table.closest(".reader__grid-wrap");
    if (!wrap) {
      return null;
    }
    var previous = wrap.previousElementSibling;
    if (previous && previous.classList.contains("reader__grid-tools")) {
      // Already enhanced: a second toolbar would be a bug, not a convenience.
      return previous.querySelector(".reader__grid-tool");
    }

    var tools = document.createElement("div");
    tools.className = "reader__grid-tools";

    var compact = document.createElement("button");
    compact.type = "button";
    compact.className = "reader__grid-tool";
    compact.textContent = "Compact";
    compact.setAttribute("aria-pressed", "false");
    compact.addEventListener("click", function () {
      var on = compact.getAttribute("aria-pressed") !== "true";
      compact.setAttribute("aria-pressed", on ? "true" : "false");
      setCompact(table, on);
    });

    var resetButton = document.createElement("button");
    resetButton.type = "button";
    resetButton.className = "reader__grid-tool";
    resetButton.textContent = "Reset columns";
    resetButton.addEventListener("click", function () {
      reset(table);
    });

    tools.appendChild(compact);
    tools.appendChild(resetButton);
    wrap.parentNode.insertBefore(tools, wrap);
    return compact;
  }

  function wireHandle(table, handle, index) {
    var dragging = null;

    handle.addEventListener("pointerdown", function (event) {
      if (event.button !== undefined && event.button !== 0) {
        return;
      }
      var start = widths(table);
      dragging = {
        x: event.clientX,
        width: start[index],
        values: start
      };
      // Freeze the current layout before the first move, so the drag is a delta from what the
      // reader already sees.
      apply(table, start);
      if (handle.setPointerCapture) {
        handle.setPointerCapture(event.pointerId);
      }
      event.preventDefault();
    });

    handle.addEventListener("pointermove", function (event) {
      if (!dragging) {
        return;
      }
      resize(table, index, dragging.width + (event.clientX - dragging.x));
    });

    function stop(event) {
      if (!dragging) {
        return;
      }
      dragging = null;
      if (handle.releasePointerCapture && event.pointerId !== undefined) {
        try {
          handle.releasePointerCapture(event.pointerId);
        } catch (error) {
          /* the capture was already lost; nothing to release */
        }
      }
    }

    handle.addEventListener("pointerup", stop);
    handle.addEventListener("pointercancel", stop);

    handle.addEventListener("keydown", function (event) {
      var current = widths(table)[index] || 0;
      var step = event.shiftKey ? SHIFT_STEP : ARROW_STEP;
      if (event.key === "ArrowLeft") {
        resize(table, index, current - step);
      } else if (event.key === "ArrowRight") {
        resize(table, index, current + step);
      } else if (event.key === "Home") {
        reset(table);
      } else {
        return;
      }
      // Only now: an arrow key inside a resizer belongs to the resizer, and one anywhere else on
      // the page belongs to the page (horizontal scroll, a carousel, anything).
      event.preventDefault();
    });
  }

  function enhance(table) {
    var stored = read(storageKey(table)) || {};
    var compactButton = buildTools(table);

    headerCells(table).forEach(function (cell, index) {
      if (index === 0) {
        // The first column is the row's identifier and stays pinned; it is the one the reader
        // never needs to widen, and its handle would sit on the paragraph's text.
        return;
      }
      var handle = cell.querySelector(".reader__grid-resizer");
      if (handle) {
        wireHandle(table, handle, index);
      }
    });

    var values = stored.widths && stored.widths.length === columns(table).length
      ? stored.widths
      : widths(table);
    apply(table, values);

    if (stored.compact && compactButton) {
      compactButton.setAttribute("aria-pressed", "true");
      table.setAttribute("data-compact", "");
    }
  }

  function start() {
    var tables = document.querySelectorAll("table[data-reader-grid]");
    Array.prototype.forEach.call(tables, function (table) {
      if (table.getAttribute("data-resizable") === null && columns(table).length) {
        enhance(table);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
