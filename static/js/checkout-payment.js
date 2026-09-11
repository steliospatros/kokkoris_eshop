/**
 * Checkout step 3 — payment method panels, sidebar totals, Stripe Payment Element.
 */
(function () {
    var form = document.getElementById("checkout-payment-form");
    if (!form) {
        return;
    }

    var sidebarShippingEl = document.getElementById("checkout-sidebar-shipping");
    var sidebarGrandTotalEl = document.getElementById("checkout-sidebar-grand-total");
    var submitBtn = document.getElementById("checkout-payment-submit");
    var intentInput = document.getElementById("stripe-payment-intent-id");
    var stripeErrorEl = document.getElementById("stripe-payment-error");
    var cartTotal = parseFloat(form.dataset.cartTotal || "0");
    var baseShipping = parseFloat(form.dataset.baseShipping || "0");
    var codShipping = parseFloat(form.dataset.codShipping || "0");
    var stripeEnabled = form.dataset.stripeEnabled === "true";
    var publishableKey = form.dataset.stripePublishableKey || "";
    var paymentIntentUrl = form.dataset.paymentIntentUrl || "";

    var stripe = null;
    var elements = null;
    var paymentElement = null;
    var activePaymentIntentId = "";
    var cardPaymentLoading = false;

    function formatGreekDecimal(value) {
        return value.toFixed(2).replace(".", ",");
    }

    function getCsrfToken() {
        var input = form.querySelector("[name=csrfmiddlewaretoken]");
        return input ? input.value : "";
    }

    function selectedPaymentMethod() {
        var checked = document.querySelector(".checkout-payment-option__input:checked");
        return checked ? checked.value : "";
    }

    function showStripeError(message) {
        if (!stripeErrorEl) {
            return;
        }
        if (message) {
            stripeErrorEl.textContent = message;
            stripeErrorEl.classList.remove("hidden");
        } else {
            stripeErrorEl.textContent = "";
            stripeErrorEl.classList.add("hidden");
        }
    }

    function setSubmitLoading(isLoading) {
        if (!submitBtn) {
            return;
        }
        submitBtn.disabled = isLoading;
        submitBtn.setAttribute("aria-busy", isLoading ? "true" : "false");
    }

    function updateSidebar(input) {
        if (!input || !sidebarGrandTotalEl) {
            return;
        }
        var shipping = input.value === "cash_on_delivery" ? codShipping : baseShipping;
        if (sidebarShippingEl) {
            sidebarShippingEl.textContent = shipping > 0
                ? formatGreekDecimal(shipping) + " €"
                : "Δωρεάν";
        }
        sidebarGrandTotalEl.textContent = formatGreekDecimal(cartTotal + shipping) + " €";
    }

    function showDetail(value) {
        document.querySelectorAll("[data-payment-detail]").forEach(function (panel) {
            panel.classList.toggle("hidden", panel.dataset.paymentDetail !== value);
        });
    }

    function destroyStripeElement() {
        if (paymentElement) {
            paymentElement.unmount();
            paymentElement = null;
        }
        elements = null;
        activePaymentIntentId = "";
        if (intentInput) {
            intentInput.value = "";
        }
    }

    function showStripeLoading(mountNode) {
        if (!mountNode) {
            return;
        }
        mountNode.innerHTML = "";
    }

    function mountStripeElement(clientSecret, paymentIntentId) {
        if (!stripeEnabled || !publishableKey || typeof Stripe === "undefined") {
            return;
        }
        var mountNode = document.getElementById("stripe-card-element");
        if (mountNode) {
            mountNode.innerHTML = "";
        }
        stripe = Stripe(publishableKey);
        elements = stripe.elements({ clientSecret: clientSecret, locale: "el" });
        paymentElement = elements.create("payment");
        paymentElement.mount("#stripe-card-element");
        activePaymentIntentId = paymentIntentId;
        if (intentInput) {
            intentInput.value = paymentIntentId;
        }
        showStripeError("");
    }

    function fetchPaymentIntent() {
        return fetch(paymentIntentUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCsrfToken(),
                "Content-Type": "application/json",
            },
            credentials: "same-origin",
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || "Δεν μπορέσαμε να ξεκινήσουμε την πληρωμή με κάρτα.");
                }
                return data;
            });
        });
    }

    function prepareCardPayment() {
        if (!stripeEnabled || cardPaymentLoading) {
            return Promise.resolve();
        }
        cardPaymentLoading = true;
        destroyStripeElement();
        var mountNode = document.getElementById("stripe-card-element");
        showStripeLoading(mountNode);
        showStripeError("");
        return fetchPaymentIntent().then(function (data) {
            mountStripeElement(data.clientSecret, data.paymentIntentId);
        }).catch(function (error) {
            showStripeError(error.message || "Δεν μπορέσαμε να ξεκινήσουμε την πληρωμή με κάρτα.");
        }).finally(function () {
            cardPaymentLoading = false;
        });
    }

    document.querySelectorAll(".checkout-payment-option__input").forEach(function (input) {
        input.addEventListener("change", function () {
            showDetail(input.value);
            updateSidebar(input);
            showStripeError("");
            if (input.value === "card") {
                prepareCardPayment();
            } else {
                destroyStripeElement();
            }
        });
        if (input.checked) {
            showDetail(input.value);
            updateSidebar(input);
            if (input.value === "card") {
                prepareCardPayment();
            }
        }
    });

    form.addEventListener("submit", function (event) {
        if (selectedPaymentMethod() !== "card" || !stripeEnabled) {
            return;
        }
        if (!stripe || !elements || !activePaymentIntentId) {
            event.preventDefault();
            showStripeError("Περίμενε να φορτώσει η φόρμα πληρωμής.");
            return;
        }
        event.preventDefault();
        setSubmitLoading(true);
        showStripeError("");
        stripe.confirmPayment({
            elements: elements,
            confirmParams: {
                return_url: window.location.href.split("?")[0],
            },
            redirect: "if_required",
        }).then(function (result) {
            if (result.error) {
                setSubmitLoading(false);
                showStripeError(result.error.message || "Η πληρωμή με κάρτα δεν ολοκληρώθηκε. Δοκίμασε ξανά ή επίλεξε αντικαταβολή.");
                return;
            }
            if (intentInput) {
                intentInput.value = activePaymentIntentId;
            }
            form.submit();
        }).catch(function () {
            setSubmitLoading(false);
            showStripeError("Η πληρωμή με κάρτα απέτυχε. Δοκίμασε ξανά.");
        });
    });
})();
