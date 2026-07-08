(function () {
    "use strict";

    var form = document.getElementById("catalog-filters-form");
    if (!form) {
        return;
    }

    function clearPageField() {
        form.querySelectorAll('input[name="page"]').forEach(function (input) {
            input.remove();
        });
    }

    function formatGreekPrice(value) {
        return Number(value).toFixed(2).replace(".", ",");
    }

    function syncPriceHiddenFields() {
        var minSlider = document.getElementById("price-range-min");
        var maxSlider = document.getElementById("price-range-max");
        if (!minSlider || !maxSlider) {
            return;
        }
        var minHidden = document.getElementById("price-min-hidden");
        var maxHidden = document.getElementById("price-max-hidden");
        var boundMin = parseFloat(minSlider.min);
        var boundMax = parseFloat(maxSlider.max);
        var minVal = parseFloat(minSlider.value);
        var maxVal = parseFloat(maxSlider.value);

        if (minVal <= boundMin && maxVal >= boundMax) {
            if (minHidden) {
                minHidden.value = "";
            }
            if (maxHidden) {
                maxHidden.value = "";
            }
        } else {
            if (minHidden) {
                minHidden.value = minVal.toFixed(2);
            }
            if (maxHidden) {
                maxHidden.value = maxVal.toFixed(2);
            }
        }
    }

    form.querySelectorAll('input[type="checkbox"]').forEach(function (checkbox) {
        checkbox.addEventListener("change", function () {
            clearPageField();
            syncPriceHiddenFields();
            form.submit();
        });
    });

    function initPriceRange() {
        var minSlider = document.getElementById("price-range-min");
        var maxSlider = document.getElementById("price-range-max");
        if (!minSlider || !maxSlider) {
            return;
        }

        var minLabel = document.getElementById("price-min-label");
        var maxLabel = document.getElementById("price-max-label");
        var track = document.getElementById("price-range-track");

        var boundMin = parseFloat(minSlider.min);
        var boundMax = parseFloat(maxSlider.max);
        var rangeSpan = boundMax - boundMin || 1;

        function updateTrack() {
            var minVal = parseFloat(minSlider.value);
            var maxVal = parseFloat(maxSlider.value);
            var left = ((minVal - boundMin) / rangeSpan) * 100;
            var right = ((boundMax - maxVal) / rangeSpan) * 100;
            track.style.left = left + "%";
            track.style.right = right + "%";
        }

        function syncSliders(changed) {
            var minVal = parseFloat(minSlider.value);
            var maxVal = parseFloat(maxSlider.value);

            if (minVal > maxVal) {
                if (changed === minSlider) {
                    maxSlider.value = String(minVal);
                    maxVal = minVal;
                } else {
                    minSlider.value = String(maxVal);
                    minVal = maxVal;
                }
            }

            minLabel.textContent = formatGreekPrice(minSlider.value);
            maxLabel.textContent = formatGreekPrice(maxSlider.value);
            updateTrack();
        }

        function submitPriceFilter() {
            syncPriceHiddenFields();
            clearPageField();
            form.submit();
        }

        minSlider.addEventListener("input", function () {
            syncSliders(minSlider);
        });
        maxSlider.addEventListener("input", function () {
            syncSliders(maxSlider);
        });
        minSlider.addEventListener("change", submitPriceFilter);
        maxSlider.addEventListener("change", submitPriceFilter);

        syncSliders();
        syncPriceHiddenFields();
    }

    initPriceRange();
})();
