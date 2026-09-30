(function () {
    "use strict";

    function closeSearch(search) {
        if (!search) {
            return;
        }
        search.classList.remove("is-search-open");
        var input = document.getElementById("nav-search-input");
        var results = document.getElementById("nav-search-results");
        if (input) {
            input.blur();
        }
        if (results) {
            results.classList.add("hidden");
        }
    }

    function setBrowseOpen(toggle, panel, open) {
        if (!toggle || !panel) {
            return;
        }
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        if (open) {
            panel.removeAttribute("hidden");
        } else {
            panel.setAttribute("hidden", "");
        }
    }

    function initNav() {
        var toggle = document.getElementById("nav-browse-toggle");
        var panel = document.getElementById("nav-browse-panel");
        var search = document.getElementById("nav-search");

        if (toggle && panel) {
            toggle.addEventListener("click", function () {
                var open = toggle.getAttribute("aria-expanded") !== "true";
                setBrowseOpen(toggle, panel, open);
                if (open) {
                    closeSearch(search);
                }
            });
        }

        document.addEventListener("click", function (event) {
            if (panel && toggle && !panel.contains(event.target) && !toggle.contains(event.target)) {
                setBrowseOpen(toggle, panel, false);
            }
            if (
                search &&
                search.classList.contains("is-search-open") &&
                !search.contains(event.target)
            ) {
                closeSearch(search);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                setBrowseOpen(toggle, panel, false);
                closeSearch(search);
            }
        });
    }

    function initCatalogFilters() {
        var layout = document.querySelector(".catalog-layout");
        var toggle = document.getElementById("catalog-filters-toggle");
        var panel = document.getElementById("catalog-filters-panel");
        if (!layout || !toggle || !panel) {
            return;
        }

        function setOpen(open) {
            layout.classList.toggle("is-filters-open", open);
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
            document.documentElement.classList.toggle("is-catalog-filters-open", open);
        }

        if (toggle.querySelector(".catalog-filters-toggle__dot")) {
            setOpen(true);
        }

        toggle.addEventListener("click", function (event) {
            event.stopPropagation();
            setOpen(!layout.classList.contains("is-filters-open"));
        });

        layout.addEventListener("click", function (event) {
            if (
                layout.classList.contains("is-filters-open") &&
                !panel.contains(event.target) &&
                !toggle.contains(event.target)
            ) {
                setOpen(false);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                setOpen(false);
            }
        });
    }

    initNav();
    initCatalogFilters();
})();
