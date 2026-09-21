(function () {
    "use strict";

    var form = document.getElementById("checkout-address-form");
    if (!form) {
        return;
    }

    var floorRow = form.querySelector(".account-detail-row--floor");

    function floorValueInput() {
        return floorRow ? floorRow.querySelector(".account-floor-value") : null;
    }

    function dismissAddressSuggestions() {
        document.querySelectorAll(".pac-container").forEach(function (el) {
            el.style.display = "none";
        });
    }

    function floorPresetValues() {
        return Array.prototype.map.call(
            floorRow.querySelectorAll(
                ".account-floor-picker__option:not(.account-floor-picker__option--other)"
            ),
            function (btn) {
                return btn.getAttribute("data-value") || "";
            }
        );
    }

    function highlightFloorSelection(value) {
        var presets = floorPresetValues();
        var isCustom = !!(value && presets.indexOf(value) === -1);
        floorRow.querySelectorAll(".account-floor-picker__option").forEach(function (btn) {
            var optionValue = btn.getAttribute("data-value");
            var selected = optionValue === "__other__" ? isCustom : optionValue === value;
            btn.classList.toggle("account-floor-picker__option--selected", selected);
            btn.setAttribute("aria-selected", selected ? "true" : "false");
        });
    }

    function selectFloor(value) {
        var input = floorValueInput();
        if (!input) {
            return;
        }
        input.value = value;
        highlightFloorSelection(value);
    }

    if (floorRow) {
        var otherInput = floorRow.querySelector(".account-floor-other");
        floorRow.querySelectorAll(".account-floor-picker__option").forEach(function (btn) {
            btn.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                dismissAddressSuggestions();
                var value = btn.getAttribute("data-value");
                if (value === "__other__") {
                    highlightFloorSelection("__other__");
                    otherInput.classList.remove("hidden");
                    otherInput.focus();
                    return;
                }
                otherInput.classList.add("hidden");
                otherInput.value = "";
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
})();
