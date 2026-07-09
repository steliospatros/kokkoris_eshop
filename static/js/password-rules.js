(function () {
    "use strict";

    var MIN_LENGTH = 8;

    function firstPasswordError(password) {
        if (password.length < MIN_LENGTH) {
            return "Ο κωδικός πρέπει να έχει τουλάχιστον 8 χαρακτήρες.";
        }
        if (!/\d/.test(password)) {
            return "Ο κωδικός πρέπει να περιλαμβάνει τουλάχιστον έναν αριθμό.";
        }
        return "";
    }

    function bindPasswordRules(input, errorEl) {
        if (!input || !errorEl) {
            return;
        }

        function update() {
            var value = input.value;
            if (!value) {
                errorEl.textContent = "";
                errorEl.classList.add("hidden");
                input.classList.remove("border-red-500");
                return;
            }

            var message = firstPasswordError(value);
            if (message) {
                errorEl.textContent = message;
                errorEl.classList.remove("hidden");
                input.classList.add("border-red-500");
                return;
            }

            errorEl.textContent = "";
            errorEl.classList.add("hidden");
            input.classList.remove("border-red-500");
        }

        input.addEventListener("input", update);
        input.addEventListener("blur", update);
    }

    window.kokkorisPasswordRules = {
        firstPasswordError: firstPasswordError,
        bindPasswordRules: bindPasswordRules,
    };

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-password-rules]").forEach(function (input) {
            var errorId = input.getAttribute("aria-describedby");
            var errorEl = errorId ? document.getElementById(errorId) : null;
            bindPasswordRules(input, errorEl);
        });
    });
})();
