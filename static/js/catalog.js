(function () {
    "use strict";

    var grid = document.getElementById("catalog-grid");
    if (!grid) {
        return;
    }

    var userAuthenticated = grid.dataset.userAuthenticated === "true";
    var loginUrl = "/accounts/login/";

    function getCookie(name) {
        var match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
        return match ? decodeURIComponent(match[2]) : "";
    }

    function csrfToken() {
        return getCookie("csrftoken");
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
            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || "Σφάλμα δικτύου.");
                }
                return data;
            });
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

    function cardCanAdd(card) {
        return card.dataset.canAdd === "true";
    }

    function cardIsOnOrder(card) {
        return card.dataset.onOrder === "true";
    }

    function cardButtonLabel(card) {
        return card.dataset.buttonLabel || "Αγορά";
    }

    function footerBgClass(card) {
        if (!cardCanAdd(card)) {
            return "bg-slate-400";
        }
        if (cardIsOnOrder(card)) {
            return "bg-kokkoris-blue";
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

    function renderStepper(card, quantity) {
        var footer = card.querySelector(".product-card-footer");
        if (!footer) {
            return;
        }
        var variantId = card.dataset.variantId;
        var maxStock = cardMaxStock(card);
        var plusDisabled =
            maxStock !== null && quantity >= maxStock
                ? " disabled"
                : "";
        setFooterBg(card, footer);
        footer.innerHTML =
            '<div class="cart-stepper flex items-center justify-between px-3 py-2" data-variant-id="' +
            variantId +
            '">' +
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
        var variantId = card.dataset.variantId;
        if (!cardCanAdd(card)) {
            setFooterBg(card, footer);
            footer.innerHTML =
                '<button type="button" disabled class="cart-add w-full py-2 text-sm font-poppins font-medium uppercase tracking-wider cursor-not-allowed opacity-80" data-variant-id="' +
                variantId +
                '">Αγορά</button>';
            return;
        }
        setFooterBg(card, footer);
        var hoverClass = cardIsOnOrder(card) ? "hover:bg-blue-900" : "hover:bg-kokkoris-teal-mid";
        footer.innerHTML =
            '<button type="button" class="cart-add w-full py-2 text-sm font-poppins font-medium uppercase tracking-wider transition-colors ' +
            hoverClass +
            '" data-variant-id="' +
            variantId +
            '">' +
            cardButtonLabel(card) +
            "</button>";
    }

    function handleCartError(error) {
        window.alert(error.message || "Δεν ήταν δυνατή η ενημέρωση του καλαθιού.");
    }

    function addToCart(card, variantId) {
        if (!cardCanAdd(card)) {
            return;
        }
        postJson("/cart/add/", { variant_id: parseInt(variantId, 10) })
            .then(function (data) {
                renderStepper(card, data.quantity);
                updateNavBadge(data.total_items);
            })
            .catch(handleCartError);
    }

    function updateQuantity(card, variantId, quantity) {
        var maxStock = cardMaxStock(card);
        if (maxStock !== null && quantity > maxStock) {
            handleCartError(new Error("Μόνο " + maxStock + " τεμάχια διαθέσιμα."));
            return;
        }
        postJson("/cart/update/", {
            variant_id: parseInt(variantId, 10),
            quantity: quantity,
        })
            .then(function (data) {
                if (data.quantity > 0) {
                    renderStepper(card, data.quantity);
                } else {
                    renderBuyButton(card);
                }
                updateNavBadge(data.total_items);
            })
            .catch(handleCartError);
    }

    function toggleWishlist(button) {
        if (!userAuthenticated) {
            window.location.href = loginUrl + "?next=" + encodeURIComponent(window.location.pathname);
            return;
        }

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
            })
            .catch(handleCartError);
    }

    grid.addEventListener("click", function (event) {
        var target = event.target;

        var addBtn = target.closest(".cart-add");
        if (addBtn) {
            if (addBtn.disabled) {
                return;
            }
            var card = addBtn.closest(".product-card");
            addToCart(card, addBtn.dataset.variantId);
            return;
        }

        var minusBtn = target.closest(".qty-minus");
        if (minusBtn) {
            var stepper = minusBtn.closest(".cart-stepper");
            var cardMinus = minusBtn.closest(".product-card");
            var valueEl = stepper.querySelector(".qty-value");
            var nextQty = Math.max(0, parseInt(valueEl.textContent, 10) - 1);
            updateQuantity(cardMinus, stepper.dataset.variantId, nextQty);
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
            updateQuantity(cardPlus, stepperPlus.dataset.variantId, nextQtyPlus);
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
            updateNavBadge(data.total_items || 0);
        })
        .catch(function () {});
})();
