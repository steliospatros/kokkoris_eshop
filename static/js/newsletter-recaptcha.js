(function () {
    var form = document.getElementById("newsletter-form");
    var tokenInput = document.getElementById("g-recaptcha-response");
    var siteKey = window.RECAPTCHA_SITE_KEY;

    if (!form || !tokenInput || !siteKey) {
        return;
    }

    form.addEventListener("submit", function (event) {
        if (typeof grecaptcha === "undefined") {
            return;
        }

        event.preventDefault();

        grecaptcha.ready(function () {
            grecaptcha.execute(siteKey, { action: "newsletter_subscribe" }).then(function (token) {
                tokenInput.value = token;
                form.submit();
            });
        });
    });
})();
