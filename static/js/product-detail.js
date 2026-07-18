(function () {
    "use strict";

    var root = document.getElementById("product-detail");
    if (!root) {
        return;
    }

    var sizePicker = document.getElementById("pd-size-picker");
    var skuEl = document.getElementById("pd-sku");
    var availabilityEl = document.getElementById("pd-availability");
    var priceEl = document.getElementById("pd-price");
    var unitPriceEl = document.getElementById("pd-unit-price");
    var cartFooter = document.getElementById("pd-cart-footer");

    function getCookie(name) {
        var match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
        return match ? decodeURIComponent(match[2]) : "";
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            credentials: "same-origin",
            body: JSON.stringify(payload),
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || "Σφάλμα δικτύου.");
                }
                return data;
            });
        });
    }

    function syncCartUi(total) {
        if (window.KokkorisCart && window.KokkorisCart.updateNavBadge) {
            window.KokkorisCart.updateNavBadge(total);
        }
        if (window.KokkorisCart && window.KokkorisCart.invalidatePreview) {
            window.KokkorisCart.invalidatePreview();
        }
    }

    function footerCanAdd() {
        return cartFooter && cartFooter.dataset.canAdd === "true";
    }

    function footerOnOrder() {
        return cartFooter && cartFooter.dataset.onOrder === "true";
    }

    function footerMaxStock() {
        if (!cartFooter || !cartFooter.dataset.maxStock) {
            return null;
        }
        var value = parseInt(cartFooter.dataset.maxStock, 10);
        return isNaN(value) ? null : value;
    }

    function renderCartFooterFromState(variantId, quantity) {
        if (!cartFooter) {
            return;
        }

        var canAdd = footerCanAdd();
        var onOrder = footerOnOrder();
        var buttonLabel = cartFooter.dataset.buttonLabel || "Αγορά";
        var maxStock = footerMaxStock();

        cartFooter.classList.remove("bg-slate-400", "bg-kokkoris-teal-dark", "bg-kokkoris-blue");
        if (!canAdd) {
            cartFooter.classList.add("bg-slate-400");
        } else if (onOrder) {
            cartFooter.classList.add("bg-kokkoris-blue");
        } else {
            cartFooter.classList.add("bg-kokkoris-teal-dark");
        }

        if (quantity > 0) {
            var plusDisabled = maxStock !== null && quantity >= maxStock ? " disabled" : "";
            cartFooter.innerHTML =
                '<div class="cart-stepper flex items-center justify-between px-6 py-3" data-variant-id="' +
                variantId +
                '">' +
                '<button type="button" class="qty-minus w-8 h-8 rounded-full border border-white/40 hover:bg-white/10 text-xl leading-none" aria-label="Μείωση">−</button>' +
                '<span class="qty-value font-semibold text-lg min-w-[2rem] text-center">' +
                quantity +
                "</span>" +
                '<button type="button" class="qty-plus w-8 h-8 rounded-full border border-white/40 hover:bg-white/10 text-xl leading-none"' +
                plusDisabled +
                ' aria-label="Αύξηση">+</button>' +
                "</div>";
            return;
        }

        if (canAdd) {
            cartFooter.innerHTML =
                '<button type="button" class="cart-add w-full py-3.5 text-sm font-poppins font-medium uppercase tracking-wider" data-variant-id="' +
                variantId +
                '">' +
                buttonLabel +
                "</button>";
            return;
        }

        cartFooter.innerHTML =
            '<button type="button" disabled class="cart-add w-full py-3.5 text-sm font-poppins font-medium uppercase tracking-wider opacity-80 cursor-not-allowed">Αγορά</button>';
    }

    function renderCartFooter(btn) {
        if (!cartFooter || !btn) {
            return;
        }

        cartFooter.dataset.variantId = btn.dataset.variantId;
        cartFooter.dataset.canAdd = btn.dataset.canAdd;
        cartFooter.dataset.onOrder = btn.dataset.onOrder;
        cartFooter.dataset.buttonLabel = btn.dataset.buttonLabel || "Αγορά";
        if (btn.dataset.maxStock) {
            cartFooter.dataset.maxStock = btn.dataset.maxStock;
        } else {
            delete cartFooter.dataset.maxStock;
        }

        var qty = parseInt(btn.dataset.cartQty || "0", 10);
        renderCartFooterFromState(btn.dataset.variantId, qty);
    }

    function syncActiveSizeQty(qty) {
        if (!sizePicker) {
            return;
        }
        var active = sizePicker.querySelector('.pd-size-btn[aria-pressed="true"]');
        if (active) {
            active.dataset.cartQty = String(qty);
        }
    }

    function selectVariant(btn) {
        if (!btn) {
            return;
        }

        if (sizePicker) {
            sizePicker.querySelectorAll(".pd-size-btn").forEach(function (el) {
                var active = el === btn;
                el.setAttribute("aria-pressed", active ? "true" : "false");
                el.classList.toggle("border-kokkoris-teal-dark", active);
                el.classList.toggle("bg-kokkoris-brand-cell", active);
                el.classList.toggle("text-kokkoris-teal-dark", active);
                el.classList.toggle("font-semibold", active);
                el.classList.toggle("border-slate-300", !active);
                el.classList.toggle("text-slate-700", !active);
            });
        }

        if (skuEl) {
            if (btn.dataset.sku) {
                skuEl.innerHTML = 'Κωδικός: <span class="font-medium text-slate-700">' + btn.dataset.sku + "</span>";
            } else {
                skuEl.textContent = "";
            }
        }

        if (availabilityEl) {
            availabilityEl.textContent = btn.dataset.availabilityLabel || "";
            availabilityEl.className =
                "mt-1 text-sm font-medium font-inter " + (btn.dataset.availabilityClass || "");
        }

        if (priceEl) {
            priceEl.textContent = (btn.dataset.price || "") + " €";
        }

        if (unitPriceEl) {
            var unitPrice = btn.dataset.unitPrice;
            var unitLabel = btn.dataset.unitLabel;
            unitPriceEl.textContent = unitPrice ? unitPrice + " € / " + unitLabel : "";
        }

        renderCartFooter(btn);

        var url = new URL(window.location.href);
        url.searchParams.set("variant", btn.dataset.variantId);
        window.history.replaceState({}, "", url.toString());
    }

    if (sizePicker) {
        sizePicker.addEventListener("click", function (event) {
            var btn = event.target.closest(".pd-size-btn");
            if (btn) {
                selectVariant(btn);
            }
        });
    }

    root.addEventListener("click", function (event) {
        var wishlistBtn = event.target.closest("#pd-wishlist");
        if (wishlistBtn) {
            postJson("/wishlist/toggle/", {
                product_id: parseInt(wishlistBtn.dataset.productId, 10),
            })
                .then(function (data) {
                    var icon = wishlistBtn.querySelector("svg");
                    if (data.wishlisted) {
                        icon.classList.remove("fill-none", "stroke-kokkoris-teal-dark");
                        icon.classList.add("fill-kokkoris-dot-pink", "stroke-kokkoris-dot-pink");
                        wishlistBtn.setAttribute("aria-pressed", "true");
                    } else {
                        icon.classList.add("fill-none", "stroke-kokkoris-teal-dark");
                        icon.classList.remove("fill-kokkoris-dot-pink", "stroke-kokkoris-dot-pink");
                        wishlistBtn.setAttribute("aria-pressed", "false");
                    }
                })
                .catch(function (err) {
                    window.alert(err.message);
                });
            return;
        }

        var addBtn = event.target.closest("#pd-cart-footer .cart-add");
        if (addBtn && !addBtn.disabled && footerCanAdd()) {
            postJson("/cart/add/", { variant_id: parseInt(addBtn.dataset.variantId, 10) })
                .then(function (data) {
                    renderCartFooterFromState(addBtn.dataset.variantId, data.quantity);
                    syncActiveSizeQty(data.quantity);
                    syncCartUi(data.total_items);
                })
                .catch(function (err) {
                    window.alert(err.message);
                });
            return;
        }

        var minusBtn = event.target.closest("#pd-cart-footer .qty-minus");
        if (minusBtn) {
            var stepper = minusBtn.closest(".cart-stepper");
            var valueEl = stepper.querySelector(".qty-value");
            var nextQty = Math.max(0, parseInt(valueEl.textContent, 10) - 1);
            postJson("/cart/update/", {
                variant_id: parseInt(stepper.dataset.variantId, 10),
                quantity: nextQty,
            })
                .then(function (data) {
                    renderCartFooterFromState(stepper.dataset.variantId, data.quantity);
                    syncActiveSizeQty(data.quantity);
                    syncCartUi(data.total_items);
                })
                .catch(function (err) {
                    window.alert(err.message);
                });
            return;
        }

        var plusBtn = event.target.closest("#pd-cart-footer .qty-plus");
        if (plusBtn && !plusBtn.disabled) {
            var stepperPlus = plusBtn.closest(".cart-stepper");
            var valuePlus = stepperPlus.querySelector(".qty-value");
            var next = parseInt(valuePlus.textContent, 10) + 1;
            var maxStock = footerMaxStock();
            if (maxStock !== null && next > maxStock) {
                window.alert("Μόνο " + maxStock + " τεμάχια διαθέσιμα.");
                return;
            }
            postJson("/cart/update/", {
                variant_id: parseInt(stepperPlus.dataset.variantId, 10),
                quantity: next,
            })
                .then(function (data) {
                    renderCartFooterFromState(stepperPlus.dataset.variantId, data.quantity);
                    syncActiveSizeQty(data.quantity);
                    syncCartUi(data.total_items);
                })
                .catch(function (err) {
                    window.alert(err.message);
                });
        }
    });

    /* Description / ingredients tabs */
    (function initInfoTabs() {
        var root = document.getElementById("pd-info-tabs");
        if (!root) {
            return;
        }

        var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-pd-tab]"));
        var panels = Array.prototype.slice.call(root.querySelectorAll("[data-pd-panel]"));
        if (!tabs.length) {
            return;
        }

        function activate(name, focusTab) {
            tabs.forEach(function (tab) {
                var active = tab.getAttribute("data-pd-tab") === name;
                tab.classList.toggle("is-active", active);
                tab.setAttribute("aria-selected", active ? "true" : "false");
                tab.tabIndex = active ? 0 : -1;
                if (active && focusTab) {
                    tab.focus();
                }
            });
            panels.forEach(function (panel) {
                var active = panel.getAttribute("data-pd-panel") === name;
                panel.hidden = !active;
                panel.classList.toggle("is-hidden", !active);
            });
        }

        root.addEventListener("click", function (event) {
            var tab = event.target.closest("[data-pd-tab]");
            if (!tab || !root.contains(tab)) {
                return;
            }
            activate(tab.getAttribute("data-pd-tab"), false);
        });

        root.addEventListener("keydown", function (event) {
            var tab = event.target.closest("[data-pd-tab]");
            if (!tab || !root.contains(tab)) {
                return;
            }
            var index = tabs.indexOf(tab);
            if (index < 0) {
                return;
            }
            var next = -1;
            if (event.key === "ArrowRight" || event.key === "ArrowDown") {
                next = (index + 1) % tabs.length;
            } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                next = (index - 1 + tabs.length) % tabs.length;
            } else if (event.key === "Home") {
                next = 0;
            } else if (event.key === "End") {
                next = tabs.length - 1;
            }
            if (next < 0) {
                return;
            }
            event.preventDefault();
            activate(tabs[next].getAttribute("data-pd-tab"), true);
        });
    })();

    /* Hover zoom — magnify under cursor while mouse is over the image */
    (function initHoverZoom() {
        var gallery = document.getElementById("pd-hover-zoom");
        var image = document.getElementById("pd-main-image");
        if (!gallery || !image) {
            return;
        }

        var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
        if (!finePointer.matches) {
            return;
        }

        var ZOOM = 2.4;
        gallery.style.setProperty("--pd-zoom-scale", String(ZOOM));

        function setOrigin(event) {
            var rect = gallery.getBoundingClientRect();
            if (!rect.width || !rect.height) {
                return;
            }
            var x = ((event.clientX - rect.left) / rect.width) * 100;
            var y = ((event.clientY - rect.top) / rect.height) * 100;
            x = Math.max(0, Math.min(100, x));
            y = Math.max(0, Math.min(100, y));
            image.style.transformOrigin = x + "% " + y + "%";
        }

        gallery.addEventListener("mouseenter", function (event) {
            gallery.classList.add("is-zooming");
            setOrigin(event);
        });

        gallery.addEventListener("mousemove", function (event) {
            if (!gallery.classList.contains("is-zooming")) {
                gallery.classList.add("is-zooming");
            }
            setOrigin(event);
        });

        gallery.addEventListener("mouseleave", function () {
            gallery.classList.remove("is-zooming");
            image.style.transformOrigin = "center center";
        });
    })();
})();
