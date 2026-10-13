(function () {
  "use strict";
  function store() {
    try { var s = window.localStorage; s.getItem("necropsy:probe"); return s; } catch (e) { return null; }
  }
  var storage = store();
  var root = document.documentElement;

  // Theme: follows the system unless the reader picks one; the choice is optional to store.
  var themeButton = document.getElementById("theme-toggle");
  function applyTheme(theme) {
    if (theme === "light" || theme === "dark") { root.setAttribute("data-theme", theme); }
    else { root.removeAttribute("data-theme"); }
    if (themeButton) {
      var current = root.getAttribute("data-theme") || "system";
      themeButton.textContent = "Theme: " + current;
    }
  }
  var saved = null;
  if (storage) { try { saved = storage.getItem("necropsy:theme"); } catch (e) { saved = null; } }
  applyTheme(saved);
  if (themeButton) {
    themeButton.addEventListener("click", function () {
      var current = root.getAttribute("data-theme");
      var next = current === "dark" ? "light" : current === "light" ? null : "dark";
      applyTheme(next);
      if (storage) { try { if (next) { storage.setItem("necropsy:theme", next); } else { storage.removeItem("necropsy:theme"); } } catch (e) {} }
    });
  }

  // In-page jumps move keyboard focus to the boss heading; the compact picker closes.
  var picker = document.getElementById("boss-picker");
  function focusSection(id) {
    var section = document.getElementById(id);
    if (!section) { return; }
    var heading = section.querySelector("h1, h2");
    if (heading) { heading.focus({ preventScroll: true }); }
  }
  document.addEventListener("click", function (event) {
    var link = event.target && event.target.closest ? event.target.closest("a[href^='#']") : null;
    if (!link) { return; }
    var id = link.getAttribute("href").slice(1);
    if (picker && picker.contains(link)) { picker.open = false; }
    if (id === "overview" || id.indexOf("boss-") === 0) { window.setTimeout(function () { focusSection(id); }, 0); }
  });

  // Wide screens: mark the boss currently on screen in the side navigation.
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".sidenav a[href^='#']"));
  function markCurrent(id) {
    navLinks.forEach(function (a) {
      if (a.getAttribute("href") === "#" + id) { a.setAttribute("aria-current", "location"); }
      else { a.removeAttribute("aria-current"); }
    });
  }
  if ("IntersectionObserver" in window && navLinks.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { if (entry.isIntersecting) { markCurrent(entry.target.id); } });
    }, { rootMargin: "-20% 0px -70% 0px" });
    Array.prototype.forEach.call(document.querySelectorAll("#overview, section.boss"), function (s) { observer.observe(s); });
  }
  if (window.location.hash) { markCurrent(window.location.hash.slice(1)); }

  // Review marks: local annotations, never part of the analysis.
  var boxes = Array.prototype.slice.call(document.querySelectorAll("input[data-review-key]"));
  boxes.forEach(function (box) {
    var key = box.getAttribute("data-review-key");
    if (storage) { try { box.checked = storage.getItem(key) === "1"; } catch (e) {} }
    box.addEventListener("change", function () {
      if (!storage) { return; }
      try { if (box.checked) { storage.setItem(key, "1"); } else { storage.removeItem(key); } } catch (e) {}
    });
  });
  var status = document.getElementById("review-status");
  if (status) {
    status.textContent = storage
      ? "Review marks are saved only in this browser, for this exact analysis."
      : "This browser does not allow saving review marks; they last until you close the page.";
  }
  var reset = document.getElementById("reset-reviews");
  if (reset) {
    reset.addEventListener("click", function () {
      boxes.forEach(function (box) {
        box.checked = false;
        if (storage) { try { storage.removeItem(box.getAttribute("data-review-key")); } catch (e) {} }
      });
    });
  }

  // Print: open every disclosure, then restore what the reader had open.
  var opened = null;
  window.addEventListener("beforeprint", function () {
    var all = Array.prototype.slice.call(document.querySelectorAll("details"));
    opened = all.map(function (d) { return d.open; });
    all.forEach(function (d) { d.open = true; });
  });
  window.addEventListener("afterprint", function () {
    if (!opened) { return; }
    var all = Array.prototype.slice.call(document.querySelectorAll("details"));
    all.forEach(function (d, i) { d.open = !!opened[i]; });
    opened = null;
  });
})();
