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
  });
  set(lang);
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();
})();
