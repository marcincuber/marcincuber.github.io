(() => {
  "use strict";

  document.documentElement.classList.replace("no-js", "js");

  const THEME_STORAGE_KEY = "mc-theme";
  const themeToggle = document.querySelector("[data-theme-toggle]");

  const applyTheme = (theme, persist = false) => {
    const selectedTheme = theme === "dark" ? "dark" : "light";
    const isDark = selectedTheme === "dark";

    document.documentElement.dataset.theme = selectedTheme;
    if (themeToggle) {
      themeToggle.setAttribute("aria-pressed", String(isDark));
      themeToggle.setAttribute("title", isDark ? "Use light theme" : "Use dark theme");
    }

    if (!persist) return;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, selectedTheme);
    } catch {
      // The active theme still works when storage is unavailable.
    }
  };

  if (themeToggle) {
    applyTheme(document.documentElement.dataset.theme);
    themeToggle.addEventListener("click", () => {
      const nextTheme =
        document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(nextTheme, true);
    });

    window.addEventListener("storage", (event) => {
      if (event.key === THEME_STORAGE_KEY) applyTheme(event.newValue);
    });
  }

  const toggle = document.querySelector("[data-nav-toggle]");
  const navigation = document.querySelector(".site-nav");

  const closeNavigation = () => {
    if (!toggle || !navigation) return;
    toggle.setAttribute("aria-expanded", "false");
    navigation.classList.remove("is-open");
  };

  if (toggle && navigation) {
    toggle.addEventListener("click", () => {
      const isOpen = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!isOpen));
      navigation.classList.toggle("is-open", !isOpen);
    });

    navigation.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest("a")) {
        closeNavigation();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        closeNavigation();
        toggle.focus();
      }
    });

    document.addEventListener("click", (event) => {
      if (
        event.target instanceof Node &&
        !navigation.contains(event.target) &&
        !toggle.contains(event.target)
      ) {
        closeNavigation();
      }
    });
  }

  const revealItems = [...document.querySelectorAll("[data-reveal]")];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver(
      (entries, currentObserver) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          currentObserver.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8%", threshold: 0.08 },
    );
    revealItems.forEach((item) => observer.observe(item));
  }

  const portraitTrigger = document.querySelector("[data-portrait-open]");
  const portraitDialog = document.querySelector("[data-portrait-dialog]");
  const portraitClose = document.querySelector("[data-portrait-close]");

  if (
    portraitTrigger instanceof HTMLElement &&
    "HTMLDialogElement" in window &&
    portraitDialog instanceof HTMLDialogElement &&
    typeof portraitDialog.showModal === "function"
  ) {
    let closeTimer = 0;
    let isClosing = false;

    const handleCloseTransition = (event) => {
      if (event.target === portraitDialog && event.propertyName === "opacity") {
        finishClose();
      }
    };

    const finishClose = () => {
      window.clearTimeout(closeTimer);
      portraitDialog.removeEventListener("transitionend", handleCloseTransition);
      if (portraitDialog.open) portraitDialog.close();
    };

    const closePortrait = () => {
      if (!portraitDialog.open || isClosing) return;
      isClosing = true;
      portraitDialog.classList.remove("is-active");

      if (reducedMotion) {
        finishClose();
        return;
      }

      portraitDialog.addEventListener("transitionend", handleCloseTransition);
      closeTimer = window.setTimeout(finishClose, 340);
    };

    portraitTrigger.addEventListener("click", (event) => {
      event.preventDefault();
      if (portraitDialog.open) return;

      isClosing = false;
      portraitDialog.showModal();
      document.documentElement.classList.add("has-open-dialog");
      window.requestAnimationFrame(() => {
        portraitDialog.classList.add("is-active");
        if (portraitClose instanceof HTMLElement) {
          portraitClose.focus({ preventScroll: true });
        }
      });
    });

    if (portraitClose instanceof HTMLElement) {
      portraitClose.addEventListener("click", closePortrait);
    }

    portraitDialog.addEventListener("click", (event) => {
      if (event.target === portraitDialog) closePortrait();
    });

    portraitDialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      closePortrait();
    });

    portraitDialog.addEventListener("close", () => {
      window.clearTimeout(closeTimer);
      portraitDialog.removeEventListener("transitionend", handleCloseTransition);
      portraitDialog.classList.remove("is-active");
      document.documentElement.classList.remove("has-open-dialog");
      isClosing = false;
      portraitTrigger.focus({ preventScroll: true });
    });
  }

  const printButton = document.querySelector("[data-print]");
  if (printButton) {
    printButton.addEventListener("click", () => window.print());
  }
})();
