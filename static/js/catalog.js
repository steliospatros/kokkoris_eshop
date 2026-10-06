(function () {
    "use strict";

    var root =
        document.getElementById("catalog-grid") ||
        document.getElementById("catalog-browse") ||
        document.querySelector(".offers-browse-section") ||
        document.querySelector(".favourites-browse-section");
    if (!root) {
        return;
    }
    // Homepage has multiple browse rows — listen on a shared ancestor.
    if (
        !document.getElementById("catalog-grid") &&
        !document.getElementById("catalog-browse")
    ) {
        root = document.body;
    }

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

    function updateNavBadge(total) {
        if (window.KokkorisCart && window.KokkorisCart.updateNavBadge) {
            window.KokkorisCart.updateNavBadge(total);
            return;
        }
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

    function syncCartUi(total) {
        updateNavBadge(total);
        if (window.KokkorisCart && window.KokkorisCart.invalidatePreview) {
            window.KokkorisCart.invalidatePreview();
        }
    }

    function updateWishlistBadge(total) {
        var badge = document.getElementById("nav-wishlist-badge");
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

    function cardCanAdd(card) {
        return card.dataset.canAdd === "true";
    }

    function footerBgClass(card) {
        if (!cardCanAdd(card)) {
            return "bg-slate-400";
        }
        return "bg-kokkoris-teal-dark";
    }

    function setFooterBg(card, footer) {
        footer.classList.remove("bg-slate-400", "bg-kokkoris-teal-dark", "bg-kokkoris-blue");
        footer.classList.add(footerBgClass(card));
    }

    function cardMaxStock(card) {
        if (!card.dataset.maxStock) {
            return null;
        }
        var value = parseInt(card.dataset.maxStock, 10);
        return isNaN(value) ? null : value;
    }

    function lineIdAttrs(card) {
        if (card.dataset.offerId) {
            return 'data-offer-id="' + card.dataset.offerId + '"';
        }
        return 'data-variant-id="' + card.dataset.variantId + '"';
    }

    function renderStepper(card, quantity) {
        var footer = card.querySelector(".product-card-footer");
        if (!footer) {
            return;
        }
        var maxStock = cardMaxStock(card);
        var plusDisabled =
            maxStock !== null && quantity >= maxStock
                ? " disabled"
                : "";
        setFooterBg(card, footer);
        footer.innerHTML =
            '<div class="cart-stepper flex items-center justify-between px-3 py-2" ' +
            lineIdAttrs(card) +
            ">" +
            '<button type="button" class="qty-minus w-7 h-7 rounded-full border border-white/40 hover:bg-white/10 text-lg leading-none" aria-label="Μείωση">−</button>' +
            '<span class="qty-value font-semibold text-base min-w-[1.5rem] text-center">' +
            quantity +
            "</span>" +
            '<button type="button" class="qty-plus w-7 h-7 rounded-full border border-white/40 hover:bg-white/10 text-lg leading-none disabled:opacity-40 disabled:cursor-not-allowed"' +
            plusDisabled +
            ' aria-label="Αύξηση">+</button>' +
            "</div>";
    }

    function renderBuyButton(card) {
        var footer = card.querySelector(".product-card-footer");
        if (!footer) {
            return;
        }
        if (!cardCanAdd(card)) {
            setFooterBg(card, footer);
            footer.innerHTML =
                '<button type="button" disabled class="cart-add w-full py-2 text-sm font-poppins font-medium uppercase tracking-wider cursor-not-allowed opacity-80" ' +
                lineIdAttrs(card) +
                ">Αγορά</button>";
            return;
        }
        setFooterBg(card, footer);
        footer.innerHTML =
            '<button type="button" class="cart-add w-full py-2 text-sm font-poppins font-medium uppercase tracking-wider transition-colors hover:bg-kokkoris-teal-mid" ' +
            lineIdAttrs(card) +
            ">Αγορά</button>";
    }

    function handleCartError(error) {
        var fallback = "Δεν μπορέσαμε να ενημερώσουμε το καλάθι. Δοκίμασε ξανά.";
        if (window.KokkorisNotice) {
            window.KokkorisNotice.fromError(error, fallback);
            return;
        }
        window.alert((error && error.message) || fallback);
    }

    function addToCart(card) {
        if (!cardCanAdd(card)) {
            return;
        }
        var payload = {};
        if (card.dataset.offerId) {
            payload.offer_id = parseInt(card.dataset.offerId, 10);
        } else {
            payload.variant_id = parseInt(card.dataset.variantId, 10);
        }
        postJson("/cart/add/", payload)
            .then(function (data) {
                renderStepper(card, data.quantity);
                syncCartUi(data.total_items);
            })
            .catch(handleCartError);
    }

    function updateQuantity(card, stepper, quantity) {
        var maxStock = cardMaxStock(card);
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
        postJson("/cart/update/", payload)
            .then(function (data) {
                if (data.quantity > 0) {
                    renderStepper(card, data.quantity);
                } else {
                    renderBuyButton(card);
                }
                syncCartUi(data.total_items);
            })
            .catch(handleCartError);
    }

    function toggleWishlist(button) {
        var productId = parseInt(button.dataset.productId, 10);
        postJson("/wishlist/toggle/", { product_id: productId })
            .then(function (data) {
                var icon = button.querySelector("svg");
                if (data.wishlisted) {
                    icon.classList.remove("fill-none", "stroke-kokkoris-teal-dark");
                    icon.classList.add("fill-kokkoris-dot-pink", "stroke-kokkoris-dot-pink");
                    button.setAttribute("aria-pressed", "true");
                } else {
                    icon.classList.add("fill-none", "stroke-kokkoris-teal-dark");
                    icon.classList.remove("fill-kokkoris-dot-pink", "stroke-kokkoris-dot-pink");
                    button.setAttribute("aria-pressed", "false");
                }
                updateWishlistBadge(data.total_items || 0);
                if (!data.wishlisted && window.location.pathname.indexOf("/wishlist") === 0) {
                    var card = button.closest(".product-card");
                    if (card) {
                        card.remove();
                    }
                }
            })
            .catch(handleCartError);
    }

    root.addEventListener("click", function (event) {
        var target = event.target;

        var addBtn = target.closest(".cart-add");
        if (addBtn) {
            if (addBtn.disabled) {
                return;
            }
            var card = addBtn.closest(".product-card");
            addToCart(card);
            return;
        }

        var minusBtn = target.closest(".qty-minus");
        if (minusBtn) {
            var stepper = minusBtn.closest(".cart-stepper");
            var cardMinus = minusBtn.closest(".product-card");
            var valueEl = stepper.querySelector(".qty-value");
            var nextQty = Math.max(0, parseInt(valueEl.textContent, 10) - 1);
            updateQuantity(cardMinus, stepper, nextQty);
            return;
        }

        var plusBtn = target.closest(".qty-plus");
        if (plusBtn) {
            if (plusBtn.disabled) {
                return;
            }
            var stepperPlus = plusBtn.closest(".cart-stepper");
            var cardPlus = plusBtn.closest(".product-card");
            var valueElPlus = stepperPlus.querySelector(".qty-value");
            var nextQtyPlus = parseInt(valueElPlus.textContent, 10) + 1;
            updateQuantity(cardPlus, stepperPlus, nextQtyPlus);
            return;
        }

        var wishBtn = target.closest(".wishlist-toggle");
        if (wishBtn) {
            toggleWishlist(wishBtn);
        }
    });

    fetch("/cart/status/", { credentials: "same-origin" })
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            if (!window.KokkorisCart) {
                updateNavBadge(data.total_items || 0);
            }
        })
        .catch(function () {});

    fetch("/wishlist/status/", { credentials: "same-origin" })
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            updateWishlistBadge(data.total_items || 0);
        })
        .catch(function () {});
})();
