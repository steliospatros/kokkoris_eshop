(function () {
    "use strict";

    var form = document.getElementById("checkout-address-form");
    if (!form) {
        return;
    }

    var floorRow = form.querySelector(".account-detail-row--floor");
    var changePhoneBtn = document.getElementById("checkout-change-phone");

    function floorValueInput() {
        return floorRow ? floorRow.querySelector(".account-floor-value") : null;
    }

    function selectFloor(value) {
        var input = floorValueInput();
        if (!input) {
            return;
        }
        input.value = value;
        floorRow.querySelectorAll(".account-floor-picker__option").forEach(function (btn) {
            btn.classList.toggle(
                "border-kokkoris-teal-dark",
                btn.getAttribute("data-value") === value ||
                    (btn.getAttribute("data-value") === "__other__" &&
                        floorRow.querySelectorAll(".account-floor-picker__option:not(.account-floor-picker__option--other)")
                            .length &&
                        value &&
                        !Array.prototype.some.call(
                            floorRow.querySelectorAll(
                                ".account-floor-picker__option:not(.account-floor-picker__option--other)"
                            ),
                            function (opt) {
                                return opt.getAttribute("data-value") === value;
                            }
                        ))
            );
        });
    }

    if (floorRow) {
        var otherInput = floorRow.querySelector(".account-floor-other");
        floorRow.querySelectorAll(".account-floor-picker__option").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var value = btn.getAttribute("data-value");
                if (value === "__other__") {
                    otherInput.classList.remove("hidden");
                    otherInput.focus();
                    return;
                }
                otherInput.classList.add("hidden");
                selectFloor(value);
            });
        });
        if (otherInput) {
            otherInput.addEventListener("input", function () {
                selectFloor(otherInput.value.trim());
            });
        }
        var initial = floorValueInput() ? floorValueInput().value : "";
        if (initial) {
            selectFloor(initial);
        }
    }

    if (changePhoneBtn) {
        changePhoneBtn.addEventListener("click", function () {
            if (!window.confirm("Θα χρειαστεί νέα επιβεβαίωση SMS για το νέο κινητό. Συνέχεια;")) {
                return;
            }
            fetch("/accounts/api/phone/reset/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)
                        ? decodeURIComponent(document.cookie.match(/csrftoken=([^;]+)/)[1])
                        : "",
                },
                credentials: "same-origin",
                body: "{}",
            }).then(function () {
                window.location.reload();
            });
        });
    }
})();
