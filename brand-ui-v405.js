(() => {
  const clean = value => {
    const path = (value || "/").replace(/\/+$/, "");
    return path || "/";
  };

  const current = clean(window.location.pathname);

  document.querySelectorAll(".site-nav a[href]").forEach(link => {
    const target = clean(new URL(link.href, window.location.origin).pathname);

    if (target === current) {
      link.hidden = true;
      link.setAttribute("aria-current", "page");
    }
  });

  const help = document.querySelector(".help-wrap");
  const helpButton = document.getElementById("faqHelp");

  if (help && helpButton) {
    helpButton.addEventListener("click", event => {
      event.stopPropagation();
      const open = help.classList.toggle("is-open");
      helpButton.setAttribute("aria-expanded", String(open));
    });

    document.addEventListener("click", event => {
      if (!help.contains(event.target)) {
        help.classList.remove("is-open");
        helpButton.setAttribute("aria-expanded", "false");
      }
    });

    document.addEventListener("keydown", event => {
      if (event.key === "Escape") {
        help.classList.remove("is-open");
        helpButton.setAttribute("aria-expanded", "false");
        helpButton.focus();
      }
    });
  }
})();
