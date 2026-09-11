(function () {
    document.querySelectorAll("[data-delivery-row]").forEach(function (row) {
        var toggle = row.querySelector("[data-delivery-toggle]");
        if (!toggle) {
            return;
        }
        toggle.addEventListener("click", function (event) {
            if (event.target.closest("a, button, input, label, textarea, [popover]")) {
                return;
            }
            row.classList.toggle("is-open");
        });
    });
})();
