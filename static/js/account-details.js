(function () {
    var form = document.getElementById("account-details-form");
    if (!form) {
        return;
    }

    var submitBtn = document.getElementById("account-details-submit");
    var cancelBtn = document.getElementById("account-details-cancel");
    var actionsBar = document.getElementById("account-details-actions");
    var dirtyHint = document.getElementById("account-details-hint");
    var rows = form.querySelectorAll(".account-detail-row:not(.account-detail-row--floor)");
    var floorRow = form.querySelector(".account-detail-row--floor");
    var autoFields = form.querySelectorAll("[data-auto-field]");
    var addressFields = form.querySelectorAll("[data-address-field]");

    function addressInputFor(fieldName) {
        var wrapper = form.querySelector('[data-address-field="' + fieldName + '"]');
        return wrapper ? wrapper.querySelector(".account-address-field__input") : null;
    }

    function isAddressFieldDirty(wrapper) {
        var input = wrapper.querySelector(".account-address-field__input");
        if (!input) {
            return false;
        }
        return input.value !== (wrapper.getAttribute("data-initial") || "");
    }

    function isAutoFieldDirty(wrapper) {
        var fieldName = wrapper.getAttribute("data-auto-field");
        var hidden = document.getElementById("id_" + fieldName);
        if (!hidden) {
            return false;
        }
        return hidden.value !== (wrapper.getAttribute("data-initial") || "");
    }

    function syncAddressDirtyState() {
        addressFields.forEach(function (wrapper) {
            wrapper.classList.toggle("account-address-field--dirty", isAddressFieldDirty(wrapper));
        });
        autoFields.forEach(function (wrapper) {
            wrapper.classList.toggle("account-auto-field--dirty", isAutoFieldDirty(wrapper));
        });
    }

    function rowInput(row) {
        return row.querySelector(".account-detail-row__input");
    }

    function rowDisplay(row) {
        return row.querySelector(".account-detail-row__display");
    }

    function rowEditBtn(row) {
        return row.querySelector(".account-detail-row__edit");
    }

    function displayText(value) {
        return value.trim() ? value : "—";
    }

    function isEmpty(value) {
        return !value.trim();
    }

    function isEmptyMode(row) {
        return row.classList.contains("account-detail-row--empty-field");
    }

    function isEditing(row) {
        return row.classList.contains("account-detail-row--editing");
    }

    function isRowDirty(row) {
        var input = rowInput(row);
        if (!input) {
            return false;
        }
        return input.value !== (row.getAttribute("data-initial") || "");
    }

    function setEditButtonState(row, editing) {
        var btn = rowEditBtn(row);
        if (!btn) {
            return;
        }
        btn.setAttribute("aria-pressed", editing ? "true" : "false");
        btn.classList.toggle("account-detail-row__edit--active", editing);
        btn.querySelector(".account-detail-row__icon-pencil").classList.toggle("hidden", editing);
        btn.querySelector(".account-detail-row__icon-check").classList.toggle("hidden", !editing);
    }

    function refreshDisplay(row) {
        var input = rowInput(row);
        var display = rowDisplay(row);
        if (!input || !display) {
            return;
        }
        display.textContent = displayText(input.value);
        display.classList.toggle("account-detail-row__empty", isEmpty(input.value));
        row.classList.toggle("account-detail-row--dirty", isRowDirty(row));
    }

    function applyEmptyMode(row) {
        var input = rowInput(row);
        var display = rowDisplay(row);
        var btn = rowEditBtn(row);
        if (!input || !display) {
            return;
        }
        row.classList.add("account-detail-row--empty-field");
        row.classList.remove("account-detail-row--editing");
        display.classList.add("hidden");
        input.classList.remove("hidden");
        if (btn) {
            btn.classList.add("hidden");
        }
        setEditButtonState(row, false);
    }

    function applyDisplayMode(row) {
        var input = rowInput(row);
        var display = rowDisplay(row);
        var btn = rowEditBtn(row);
        if (!input || !display) {
            return;
        }
        refreshDisplay(row);
        row.classList.remove("account-detail-row--empty-field");
        row.classList.remove("account-detail-row--editing");
        display.classList.remove("hidden");
        input.classList.add("hidden");
        if (btn) {
            btn.classList.remove("hidden");
        }
        setEditButtonState(row, false);
    }

    function enterEdit(row) {
        var input = rowInput(row);
        var display = rowDisplay(row);
        var btn = rowEditBtn(row);
        if (!input || !display) {
            return;
        }
        row.classList.remove("account-detail-row--empty-field");
        row.classList.add("account-detail-row--editing");
        display.classList.add("hidden");
        input.classList.remove("hidden");
        if (btn) {
            btn.classList.remove("hidden");
        }
        input.focus();
        if (input.setSelectionRange && input.value) {
            input.setSelectionRange(input.value.length, input.value.length);
        }
        setEditButtonState(row, true);
    }

    function exitEdit(row, revert) {
        var input = rowInput(row);
        if (!input) {
            return;
        }
        if (revert) {
            input.value = row.getAttribute("data-initial") || "";
        }
        if (isEmpty(input.value)) {
            applyEmptyMode(row);
        } else {
            applyDisplayMode(row);
        }
    }

    function floorValueInput() {
        return floorRow ? floorRow.querySelector(".account-floor-value") : null;
    }

    function isFloorDirty() {
        var input = floorValueInput();
        if (!input || !floorRow) {
            return false;
        }
        return input.value !== (floorRow.getAttribute("data-initial") || "");
    }

    function floorPresetValues() {
        if (!floorRow) {
            return [];
        }
        return Array.prototype.map.call(
            floorRow.querySelectorAll(".account-floor-picker__option:not(.account-floor-picker__option--other)"),
            function (btn) {
                return btn.getAttribute("data-value") || "";
            }
        );
    }

    function isFloorPreset(value) {
        return floorPresetValues().indexOf(value) !== -1;
    }

    function floorDisplayText(value) {
        return value.trim() ? value : "—";
    }

    function refreshFloorDisplay() {
        if (!floorRow) {
            return;
        }
        var input = floorValueInput();
        var display = floorRow.querySelector(".account-floor-display");
        if (!input || !display) {
            return;
        }
        display.textContent = floorDisplayText(input.value);
        display.classList.toggle("account-detail-row__empty", !input.value.trim());
        floorRow.classList.toggle("account-detail-row--dirty", isFloorDirty());
    }

    function highlightFloorSelection(value) {
        if (!floorRow) {
            return;
        }
        floorRow.querySelectorAll(".account-floor-picker__option").forEach(function (btn) {
            var optionValue = btn.getAttribute("data-value");
            var selected =
                optionValue === "__other__" ? value && !isFloorPreset(value) : optionValue === value;
            btn.classList.toggle("account-floor-picker__option--selected", !!selected);
        });
    }

    function setFloorEditButtonState(editing) {
        if (!floorRow) {
            return;
        }
        var btn = floorRow.querySelector(".account-detail-row__edit");
        if (!btn) {
            return;
        }
        btn.setAttribute("aria-pressed", editing ? "true" : "false");
        btn.classList.toggle("account-detail-row__edit--active", editing);
        btn.querySelector(".account-detail-row__icon-pencil").classList.toggle("hidden", editing);
        btn.querySelector(".account-detail-row__icon-check").classList.toggle("hidden", !editing);
    }

    function showFloorEditor(showOther, otherValue) {
        if (!floorRow) {
            return;
        }
        var editor = floorRow.querySelector(".account-floor-editor");
        var otherInput = floorRow.querySelector(".account-floor-other");
        var input = floorValueInput();
        if (!editor || !otherInput || !input) {
            return;
        }
        editor.classList.remove("hidden");
        highlightFloorSelection(input.value);
        if (showOther) {
            otherInput.classList.remove("hidden");
            otherInput.value = otherValue || "";
            otherInput.focus();
        } else {
            otherInput.classList.add("hidden");
            otherInput.value = "";
        }
    }

    function hideFloorEditor() {
        if (!floorRow) {
            return;
        }
        var editor = floorRow.querySelector(".account-floor-editor");
        var otherInput = floorRow.querySelector(".account-floor-other");
        if (editor) {
            editor.classList.add("hidden");
        }
        if (otherInput) {
            otherInput.classList.add("hidden");
        }
    }

    function applyFloorEmptyMode() {
        if (!floorRow) {
            return;
        }
        var input = floorValueInput();
        var display = floorRow.querySelector(".account-floor-display");
        var trigger = floorRow.querySelector(".account-floor-empty-trigger");
        var editBtn = floorRow.querySelector(".account-detail-row__edit");
        floorRow.classList.add("account-detail-row--empty-field");
        floorRow.classList.remove("account-detail-row--editing");
        if (display) {
            display.classList.add("hidden");
        }
        if (trigger) {
            trigger.classList.remove("hidden");
        }
        if (editBtn) {
            editBtn.classList.add("hidden");
        }
        hideFloorEditor();
        setFloorEditButtonState(false);
        refreshFloorDisplay();
    }

    function applyFloorDisplayMode() {
        if (!floorRow) {
            return;
        }
        var input = floorValueInput();
        var display = floorRow.querySelector(".account-floor-display");
        var trigger = floorRow.querySelector(".account-floor-empty-trigger");
        var editBtn = floorRow.querySelector(".account-detail-row__edit");
        if (!input || !display) {
            return;
        }
        refreshFloorDisplay();
        floorRow.classList.remove("account-detail-row--empty-field");
        floorRow.classList.remove("account-detail-row--editing");
        display.classList.remove("hidden");
        if (trigger) {
            trigger.classList.add("hidden");
        }
        if (editBtn) {
            editBtn.classList.remove("hidden");
        }
        hideFloorEditor();
        setFloorEditButtonState(false);
    }

    function enterFloorEdit() {
        if (!floorRow) {
            return;
        }
        var input = floorValueInput();
        var display = floorRow.querySelector(".account-floor-display");
        var trigger = floorRow.querySelector(".account-floor-empty-trigger");
        var editBtn = floorRow.querySelector(".account-detail-row__edit");
        floorRow.classList.remove("account-detail-row--empty-field");
        floorRow.classList.add("account-detail-row--editing");
        if (display) {
            display.classList.add("hidden");
        }
        if (trigger) {
            trigger.classList.add("hidden");
        }
        if (editBtn) {
            editBtn.classList.remove("hidden");
        }
        var value = input ? input.value.trim() : "";
        var showOther = value && !isFloorPreset(value);
        showFloorEditor(showOther, showOther ? value : "");
        setFloorEditButtonState(true);
    }

    function exitFloorEdit(revert) {
        if (!floorRow) {
            return;
        }
        var input = floorValueInput();
        if (!input) {
            return;
        }
        if (revert) {
            input.value = floorRow.getAttribute("data-initial") || "";
        }
        if (!input.value.trim()) {
            applyFloorEmptyMode();
        } else {
            applyFloorDisplayMode();
        }
        syncControls();
    }

    function setFloorValue(value) {
        if (!floorRow) {
            return;
        }
        var input = floorValueInput();
        if (!input) {
            return;
        }
        input.value = value;
        refreshFloorDisplay();
        syncControls();
    }

    function initFloorField() {
        if (!floorRow) {
            return;
        }
        var input = floorValueInput();
        var editBtn = floorRow.querySelector(".account-detail-row__edit");
        var trigger = floorRow.querySelector(".account-floor-empty-trigger");
        var otherInput = floorRow.querySelector(".account-floor-other");

        if (!input.value.trim()) {
            applyFloorEmptyMode();
        } else {
            applyFloorDisplayMode();
        }

        if (trigger) {
            trigger.addEventListener("click", function () {
                enterFloorEdit();
            });
        }

        if (editBtn) {
            editBtn.addEventListener("click", function () {
                if (floorRow.classList.contains("account-detail-row--editing")) {
                    exitFloorEdit(false);
                } else {
                    enterFloorEdit();
                }
            });
        }

        floorRow.querySelectorAll(".account-floor-picker__option").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var optionValue = btn.getAttribute("data-value");
                if (optionValue === "__other__") {
                    var current = input.value.trim();
                    showFloorEditor(true, isFloorPreset(current) ? "" : current);
                    return;
                }
                setFloorValue(optionValue);
                applyFloorDisplayMode();
            });
        });

        if (otherInput) {
            otherInput.addEventListener("input", function () {
                setFloorValue(otherInput.value.trim());
            });

            otherInput.addEventListener("keydown", function (event) {
                if (event.key === "Enter") {
                    event.preventDefault();
                    exitFloorEdit(false);
                }
                if (event.key === "Escape") {
                    event.preventDefault();
                    exitFloorEdit(true);
                }
            });
        }

        if (floorRow.querySelector(".account-detail-row__error")) {
            enterFloorEdit();
        }
    }

    function hasPendingChanges() {
        var changed = false;
        rows.forEach(function (row) {
            if (isRowDirty(row)) {
                changed = true;
            }
        });
        if (floorRow && isFloorDirty()) {
            changed = true;
        }
        autoFields.forEach(function (wrapper) {
            if (isAutoFieldDirty(wrapper)) {
                changed = true;
            }
        });
        addressFields.forEach(function (wrapper) {
            if (isAddressFieldDirty(wrapper)) {
                changed = true;
            }
        });
        var latInput = document.getElementById("id_latitude");
        var lngInput = document.getElementById("id_longitude");
        if (latInput && lngInput) {
            var latInitial = latInput.getAttribute("data-initial") || "";
            var lngInitial = lngInput.getAttribute("data-initial") || "";
            if (latInput.value !== latInitial || lngInput.value !== lngInitial) {
                changed = true;
            }
        }
        var addressHidden = document.getElementById("id_address");
        if (addressHidden) {
            var addressInitial = addressHidden.getAttribute("data-initial") || "";
            if (addressHidden.value !== addressInitial) {
                changed = true;
            }
        }
        var componentsInput = document.getElementById("id_address_components_json");
        if (componentsInput && componentsInput.value) {
            var componentsInitial = componentsInput.getAttribute("data-initial") || "";
            if (componentsInput.value !== componentsInitial) {
                changed = true;
            }
        }
        return changed;
    }

    function syncControls() {
        var dirty = hasPendingChanges();
        submitBtn.disabled = !dirty;
        cancelBtn.classList.toggle("hidden", !dirty);
        if (dirtyHint) {
            dirtyHint.classList.toggle("hidden", !dirty);
        }
        if (actionsBar) {
            actionsBar.classList.toggle("account-details-actions--dirty", dirty);
        }
        rows.forEach(function (row) {
            row.classList.toggle("account-detail-row--dirty", isRowDirty(row));
        });
        if (floorRow) {
            floorRow.classList.toggle("account-detail-row--dirty", isFloorDirty());
        }
        syncAddressDirtyState();
    }

    window.kokkorisAccountDetailsSync = syncControls;

    rows.forEach(function (row) {
        var editBtn = rowEditBtn(row);
        var input = rowInput(row);
        var initial = row.getAttribute("data-initial") || "";

        if (isEmpty(initial)) {
            applyEmptyMode(row);
        } else {
            applyDisplayMode(row);
        }

        if (editBtn) {
            editBtn.addEventListener("click", function () {
                if (isEditing(row)) {
                    exitEdit(row, false);
                } else {
                    enterEdit(row);
                }
                syncControls();
            });
        }

        if (input) {
            input.addEventListener("input", function () {
                row.classList.toggle("account-detail-row--dirty", isRowDirty(row));
                syncControls();
            });

            input.addEventListener("keydown", function (event) {
                if (event.key === "Escape") {
                    event.preventDefault();
                    exitEdit(row, true);
                    syncControls();
                    return;
                }
                if (event.key === "Enter" && input.tagName !== "TEXTAREA" && !isEmptyMode(row)) {
                    event.preventDefault();
                    exitEdit(row, false);
                    syncControls();
                }
            });

            input.addEventListener("blur", function () {
                window.setTimeout(function () {
                    if (isEmptyMode(row)) {
                        if (!isEmpty(input.value)) {
                            applyDisplayMode(row);
                            syncControls();
                        }
                        return;
                    }
                    if (!isEditing(row)) {
                        return;
                    }
                    if (form.contains(document.activeElement)) {
                        return;
                    }
                    exitEdit(row, false);
                    syncControls();
                }, 120);
            });
        }
    });

    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            rows.forEach(function (row) {
                exitEdit(row, true);
            });
            exitFloorEdit(true);
            autoFields.forEach(function (wrapper) {
                var fieldName = wrapper.getAttribute("data-auto-field");
                var hidden = document.getElementById("id_" + fieldName);
                var display = wrapper.querySelector(".account-auto-field__display");
                var initial = wrapper.getAttribute("data-initial") || "";
                if (hidden) {
                    hidden.value = initial;
                }
                if (display) {
                    display.value = initial;
                }
            });
            var addressHidden = document.getElementById("id_address");
            if (addressHidden) {
                addressHidden.value = addressHidden.getAttribute("data-initial") || "";
            }
            var componentsInput = document.getElementById("id_address_components_json");
            if (componentsInput) {
                componentsInput.value = componentsInput.getAttribute("data-initial") || "";
            }
            var searchInput = document.getElementById("id_address_search");
            if (searchInput) {
                searchInput.value = "";
            }
            addressFields.forEach(function (wrapper) {
                var input = wrapper.querySelector(".account-address-field__input");
                if (input) {
                    input.value = wrapper.getAttribute("data-initial") || "";
                }
            });
            var latInput = document.getElementById("id_latitude");
            var lngInput = document.getElementById("id_longitude");
            var placeInput = document.getElementById("id_address_place_id");
            if (latInput) {
                latInput.value = latInput.getAttribute("data-initial") || "";
            }
            if (lngInput) {
                lngInput.value = lngInput.getAttribute("data-initial") || "";
            }
            if (placeInput) {
                placeInput.value = placeInput.getAttribute("data-initial") || "";
            }
            syncControls();
        });
    }

    form.addEventListener("submit", function () {
        rows.forEach(function (row) {
            var input = rowInput(row);
            if (input) {
                input.classList.remove("hidden");
            }
        });
    });

    rows.forEach(function (row) {
        if (row.querySelector(".account-detail-row__error")) {
            enterEdit(row);
        }
    });

    addressFields.forEach(function (wrapper) {
        var input = wrapper.querySelector(".account-address-field__input");
        if (input) {
            input.addEventListener("input", function () {
                syncControls();
            });
        }
    });

    autoFields.forEach(function (wrapper) {
        var fieldName = wrapper.getAttribute("data-auto-field");
        var hidden = document.getElementById("id_" + fieldName);
        if (hidden) {
            hidden.addEventListener("input", function () {
                syncControls();
            });
        }
    });

    ["id_latitude", "id_longitude", "id_address_place_id", "id_address", "id_address_components_json"].forEach(function (id) {
        var input = document.getElementById(id);
        if (input && !input.getAttribute("data-initial")) {
            input.setAttribute("data-initial", input.value || "");
        }
    });

    initFloorField();
    syncControls();
})();
