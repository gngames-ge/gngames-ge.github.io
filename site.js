(function () {
  var langs = ["en", "ka", "ru"];
  var saved = null;
  try { saved = localStorage.getItem("gn-lang"); } catch (e) {}
  var q = new URLSearchParams(location.search).get("lang");
  var guess = (navigator.language || "en").slice(0, 2);
  var lang = [q, saved, guess].filter(function (l) { return langs.indexOf(l) >= 0; })[0] || "en";
  function set(l) {
    document.documentElement.lang = l;
    try { localStorage.setItem("gn-lang", l); } catch (e) {}
    document.querySelectorAll(".langs button").forEach(function (b) {
      b.classList.toggle("on", b.dataset.set === l);
    });
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".langs button");
    if (b) set(b.dataset.set);
    var g = e.target.closest("[data-scroll]");
    if (g) {
      var el = document.querySelector(".gallery");
      if (el) el.scrollBy({ left: (g.dataset.scroll === "next" ? 1 : -1) * el.clientWidth * 0.8, behavior: "smooth" });
    }
  });
  set(lang);

  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // reveal on scroll
  var io = "IntersectionObserver" in window ? new IntersectionObserver(function (es) {
    es.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
  }, { threshold: 0.12 }) : null;
  document.querySelectorAll(".rv").forEach(function (el) { io ? io.observe(el) : el.classList.add("in"); });

  if (reduce) return;

  // tilt on game tiles
  document.querySelectorAll(".tile").forEach(function (t) {
    t.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse") return;
      var r = t.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5, y2 = (e.clientY - r.top) / r.height - 0.5;
      t.style.transform = "perspective(1100px) rotateY(" + (x * 5) + "deg) rotateX(" + (-y2 * 5) + "deg)";
    });
    t.addEventListener("pointerleave", function () { t.style.transform = ""; });
  });

  // slow parallax on the game hero
  var bg = document.querySelector(".g-hero .bg");
  if (bg) window.addEventListener("scroll", function () {
    bg.style.transform = "translateY(" + (window.scrollY * 0.25) + "px) scale(1.04)";
  }, { passive: true });

  // TOC highlight on legal pages
  var links = document.querySelectorAll(".toc a");
  if (links.length && io) {
    var tio = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (en.isIntersecting) links.forEach(function (a) { a.classList.toggle("on", a.getAttribute("href") === "#" + en.target.id); });
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    document.querySelectorAll(".doc h2[id]").forEach(function (h) { tio.observe(h); });
  }
})();
