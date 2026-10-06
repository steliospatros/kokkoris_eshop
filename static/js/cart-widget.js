(function () {
    "use strict";

    var PREVIEW_URL = "/cart/preview/";
    var UPDATE_URL = "/cart/update/";
    var CLEAR_URL = "/cart/clear/";
    var STATUS_URL = "/cart/status/";
    var CART_PAGE_URL = "/accounts/cart/";

    function csrfToken() {
        return window.KokkorisNotice && window.KokkorisNotice.csrfToken
            ? window.KokkorisNotice.csrfToken()
            : "";
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken(),
            },
            credentials: "same-origin",
            body: JSON.stringify(payload),
        }).then(function (response) {
            if (window.KokkorisNotice && window.KokkorisNotice.readJsonResponse) {
                return window.KokkorisNotice.readJsonResponse(response);
            }
            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || "Η σύνδεση διακόπηκε. Έλεγξε το δίκτυό σου και δοκίμασε ξανά.");
                }
                return data;
            });
        });
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, function (ch) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
        });
    }

    function updateNavBadge(total) {
        var badge = document.getElementById("nav-cart-badge");
        if (!badge) {
            return;
        }
        if (total > 0) {
            badge.textContent = String(total);
            badge.classList.remove("hidden");
        } else {
            badge.classList.add("hidden");
        }
    }

    function lineMaxStock(lineEl) {
        if (!lineEl || !lineEl.dataset.maxStock) {
            return null;
        }
        var value = parseInt(lineEl.dataset.maxStock, 10);
        return isNaN(value) ? null : value;
    }

    function lineKeyAttrs(line) {
        if (line.offer_id) {
            return ' data-offer-id="' + line.offer_id + '"';
        }
        return ' data-variant-id="' + line.variant_id + '"';
    }

    function lineStepperAttrs(line) {
        if (line.offer_id) {
            return 'data-offer-id="' + line.offer_id + '"';
        }
        return 'data-variant-id="' + line.variant_id + '"';
    }

    function renderMiniLine(line) {
        var thumb = line.image_url
            ? '<img src="' + escapeHtml(line.image_url) + '" alt="" class="w-full h-full object-contain">'
            : '<span class="w-full h-full bg-slate-100"></span>';
        var plusDisabled =
            line.max_quantity !== null &&
            line.max_quantity !== undefined &&
            line.quantity >= line.max_quantity
                ? " disabled"
                : "";
        var maxAttr =
            line.max_quantity !== null && line.max_quantity !== undefined
                ? ' data-max-stock="' + line.max_quantity + '"'
                : "";

        return (
            '<li class="cart-line-row flex items-center gap-3 py-2.5"' +
            lineKeyAttrs(line) +
            maxAttr +
            ">" +
            '<div class="shrink-0 w-12 h-12 rounded-lg border border-slate-100 bg-slate-50 overflow-hidden flex items-center justify-center">' +
            thumb +
            "</div>" +
            '<div class="flex-1 min-w-0">' +
            '<p class="font-inter font-medium text-slate-800 text-xs leading-snug line-clamp-2">' +
            escapeHtml(line.title) +
            "</p>" +
            "</div>" +
            '<div class="cart-stepper flex items-center gap-1.5 shrink-0 bg-kokkoris-teal-dark text-white rounded-full px-1.5 py-1" ' +
            lineStepperAttrs(line) +
            ">" +
            '<button type="button" class="qty-minus w-6 h-6 rounded-full border border-white/40 hover:bg-white/10 text-base leading-none flex items-center justify-center" aria-label="Μείωση">−</button>' +
            '<span class="qty-value font-semibold text-sm min-w-[1.25rem] text-center">' +
            line.quantity +
            "</span>" +
            '<button type="button" class="qty-plus w-6 h-6 rounded-full border border-white/40 hover:bg-white/10 text-base leading-none flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"' +
            plusDisabled +
            ' aria-label="Αύξηση">+</button>' +
            "</div>" +
            '<p class="cart-line-subtotal font-inter font-semibold text-slate-800 text-xs w-14 text-right shrink-0">' +
            escapeHtml(line.subtotal_display) +
            " €</p>" +
            "</li>"
        );
    }

    function renderMiniPanel(data) {
        var panelBody = document.getElementById("nav-cart-panel-body");
        if (!panelBody) {
            return;
        }

        if (!data.lines || !data.lines.length) {
            panelBody.innerHTML =
                '<p class="px-4 py-6 text-sm text-slate-500 text-center font-inter">Το καλάθι είναι άδειο. Πρόσθεσε προϊόντα για να συνεχίσεις.</p>';
            return;
        }

        panelBody.innerHTML =
            '<ul class="divide-y divide-slate-100">' +
            data.lines.map(renderMiniLine).join("") +
            "</ul>";
    }

    function refreshCartPage(data) {
        var linesRoot = document.getElementById("cart-page-lines");
        if (!linesRoot) {
            return;
        }

        if (!data.lines || !data.lines.length) {
            window.location.reload();
            return;
        }

        data.lines.forEach(function (line) {
            var selector = line.offer_id
                ? '.cart-line-row[data-offer-id="' + line.offer_id + '"]'
                : '.cart-line-row[data-variant-id="' + line.variant_id + '"]';
            var row = linesRoot.querySelector(selector);
            if (!row) {
                return;
            }
            var valueEl = row.querySelector(".qty-value");
            var subtotalEl = row.querySelector(".cart-line-subtotal");
            var plusBtn = row.querySelector(".qty-plus");
            if (valueEl) {
                valueEl.textContent = String(line.quantity);
            }
            if (subtotalEl) {
                subtotalEl.textContent = line.subtotal_display + " €";
            }
            if (plusBtn) {
                if (
                    line.max_quantity !== null &&
                    line.max_quantity !== undefined &&
                    line.quantity >= line.max_quantity
                ) {
                    plusBtn.disabled = true;
                } else {
                    plusBtn.disabled = false;
                }
            }
        });

        var totalEl = document.getElementById("cart-page-total");
        if (totalEl && data.total_display) {
            totalEl.textContent = data.total_display + " €";
        }
    }

    function removeMissingCartPageLines(data) {
        var linesRoot = document.getElementById("cart-page-lines");
        if (!linesRoot || !data.lines) {
            return;
        }
        var activeKeys = {};
        data.lines.forEach(function (line) {
            if (line.offer_id) {
                activeKeys["o:" + line.offer_id] = true;
            } else {
                activeKeys["v:" + line.variant_id] = true;
            }
        });
        linesRoot.querySelectorAll(".cart-line-row").forEach(function (row) {
            var key = row.dataset.offerId
                ? "o:" + row.dataset.offerId
                : "v:" + row.dataset.variantId;
            if (!activeKeys[key]) {
                row.remove();
            }
        });
        if (!data.lines.length) {
            window.location.reload();
        }
    }

    var previewLoaded = false;
    var previewLoading = false;

    function loadPreview(force) {
        var panel = document.getElementById("nav-cart-panel");
        if (!panel) {
            return Promise.resolve(null);
        }
        if (previewLoaded && !force) {
            return Promise.resolve(null);
        }
        if (previewLoading) {
            return Promise.resolve(null);
        }
        previewLoading = true;
        return fetch(PREVIEW_URL, { credentials: "same-origin" })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                previewLoaded = true;
                renderMiniPanel(data);
                updateNavBadge(data.total_items || 0);
                return data;
            })
            .catch(function () {
                return null;
            })
            .finally(function () {
                previewLoading = false;
            });
    }

    function handleCartError(error) {
        var fallback = "Δεν μπορέσαμε να ενημερώσουμε το καλάθι. Δοκίμασε ξανά.";
        if (window.KokkorisNotice) {
            window.KokkorisNotice.fromError(error, fallback);
            return;
        }
        window.alert((error && error.message) || fallback);
    }

    function updateQuantity(stepper, quantity, lineEl) {
        var maxStock = lineMaxStock(lineEl);
        if (maxStock !== null && quantity > maxStock) {
            handleCartError(new Error("Μπορείς να βάλεις έως " + maxStock + " τεμάχια."));
            return;
        }

        var payload = { quantity: quantity };
        if (stepper.dataset.offerId) {
            payload.offer_id = parseInt(stepper.dataset.offerId, 10);
        } else {
            payload.variant_id = parseInt(stepper.dataset.variantId, 10);
        }

        postJson(UPDATE_URL, payload)
            .then(function () {
                return fetch(PREVIEW_URL, { credentials: "same-origin" }).then(function (response) {
                    return response.json();
                });
            })
            .then(function (data) {
                updateNavBadge(data.total_items || 0);
                renderMiniPanel(data);
                refreshCartPage(data);
                removeMissingCartPageLines(data);
                previewLoaded = true;
            })
            .catch(handleCartError);
    }

    function bindStepperClicks(root) {
        if (!root || root.dataset.cartSteppersBound === "true") {
            return;
        }
        root.dataset.cartSteppersBound = "true";
        root.addEventListener("click", function (event) {
            var minusBtn = event.target.closest(".qty-minus");
            if (minusBtn) {
                var stepper = minusBtn.closest(".cart-stepper");
                var lineEl = minusBtn.closest(".cart-line-row");
                var valueEl = stepper.querySelector(".qty-value");
                var nextQty = Math.max(0, parseInt(valueEl.textContent, 10) - 1);
                updateQuantity(stepper, nextQty, lineEl);
                return;
            }

            var plusBtn = event.target.closest(".qty-plus");
            if (plusBtn) {
                if (plusBtn.disabled) {
                    return;
                }
                var stepperPlus = plusBtn.closest(".cart-stepper");
                var lineElPlus = plusBtn.closest(".cart-line-row");
                var valueElPlus = stepperPlus.querySelector(".qty-value");
                var nextQtyPlus = parseInt(valueElPlus.textContent, 10) + 1;
                updateQuantity(stepperPlus, nextQtyPlus, lineElPlus);
            }
        });
    }

    function initNavWidget() {
        var widget = document.getElementById("nav-cart-widget");
        var panel = document.getElementById("nav-cart-panel");
        if (!widget || !panel) {
            return;
        }

        widget.addEventListener("mouseenter", function () {
            panel.classList.remove("hidden");
            loadPreview(false);
        });

        widget.addEventListener("mouseleave", function (event) {
            if (widget.contains(event.relatedTarget)) {
                return;
            }
            panel.classList.add("hidden");
        });

        widget.addEventListener("focusin", function () {
            panel.classList.remove("hidden");
            loadPreview(false);
        });

        bindStepperClicks(panel);
    }

    function initCartPage() {
        var cartPage = document.getElementById("cart-page");
        if (!cartPage) {
            return;
        }
        bindStepperClicks(cartPage);

        var clearBtn = document.getElementById("cart-clear-all");
        if (clearBtn) {
            clearBtn.addEventListener("click", function () {
                if (!window.confirm("Να αφαιρεθούν όλα τα προϊόντα από το καλάθι;")) {
                    return;
                }
                postJson(CLEAR_URL, {})
                    .then(function (data) {
                        updateNavBadge(data.total_items || 0);
                        previewLoaded = false;
                        window.location.reload();
                    })
                    .catch(handleCartError);
            });
        }
    }

    initNavWidget();
    initCartPage();

    fetch(STATUS_URL, { credentials: "same-origin" })
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            updateNavBadge(data.total_items || 0);
        })
        .catch(function () {});

    window.KokkorisCart = {
        updateNavBadge: updateNavBadge,
        loadPreview: function () {
            previewLoaded = false;
            return loadPreview(true);
        },
        invalidatePreview: function () {
            previewLoaded = false;
        },
        postJson: postJson,
    };

    var checkoutBtn = document.getElementById("cart-checkout-btn");
    if (checkoutBtn && window.kokkorisOpenAuthModal) {
        checkoutBtn.addEventListener("click", function () {
            window.kokkorisOpenAuthModal("login", checkoutBtn.dataset.checkoutUrl);
        });
    }
})();
