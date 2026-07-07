(function () {
    var STORAGE_KEY = "kokkoris_cookie_consent";

    function readConsent() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
        } catch (e) {
            return null;
        }
    }

    function writeConsent(consent) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(consent));
    }

    function getElements() {
        return {
            banner: document.getElementById("cookie-banner"),
            modal: document.getElementById("cookie-settings-modal"),
            analyticsToggle: document.getElementById("cookie-analytics"),
            marketingToggle: document.getElementById("cookie-marketing"),
        };
    }

    function applyConsentToToggles(consent) {
        var els = getElements();
        if (!els.analyticsToggle || !els.marketingToggle) {
            return;
        }
        els.analyticsToggle.checked = !!(consent && consent.analytics);
        els.marketingToggle.checked = !!(consent && consent.marketing);
    }

    function hideBanner() {
        var banner = getElements().banner;
        if (banner) {
            banner.classList.add("hidden");
        }
    }

    function showModal() {
        var modal = getElements().modal;
        if (modal) {
            modal.classList.remove("hidden");
            modal.setAttribute("aria-hidden", "false");
        }
    }

    function hideModal() {
        var modal = getElements().modal;
        if (modal) {
            modal.classList.add("hidden");
            modal.setAttribute("aria-hidden", "true");
        }
    }

    function saveConsent(analytics, marketing) {
        writeConsent({
            necessary: true,
            analytics: analytics,
            marketing: marketing,
            updatedAt: new Date().toISOString(),
        });
        hideBanner();
        hideModal();
    }

    window.kokkorisOpenCookieSettings = function () {
        var consent = readConsent();
        applyConsentToToggles(consent || { analytics: false, marketing: false });
        showModal();
    };

    document.addEventListener("DOMContentLoaded", function () {
        var els = getElements();
        var consent = readConsent();

        if (!consent && els.banner) {
            els.banner.classList.remove("hidden");
        }

        var acceptAllBtn = document.getElementById("cookie-accept-all");
        var rejectBtn = document.getElementById("cookie-reject-optional");
        var saveBtn = document.getElementById("cookie-save-preferences");
        var openSettingsBtn = document.getElementById("cookie-open-settings");
        var closeModalBtn = document.getElementById("cookie-close-modal");
        var footerSettingsBtn = document.getElementById("cookie-settings-trigger");

        if (acceptAllBtn) {
            acceptAllBtn.addEventListener("click", function () {
                saveConsent(true, true);
            });
        }

        if (rejectBtn) {
            rejectBtn.addEventListener("click", function () {
                saveConsent(false, false);
            });
        }

        if (openSettingsBtn) {
            openSettingsBtn.addEventListener("click", function () {
                window.kokkorisOpenCookieSettings();
            });
        }

        if (footerSettingsBtn) {
            footerSettingsBtn.addEventListener("click", function () {
                window.kokkorisOpenCookieSettings();
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener("click", function () {
                saveConsent(
                    !!(els.analyticsToggle && els.analyticsToggle.checked),
                    !!(els.marketingToggle && els.marketingToggle.checked)
                );
            });
        }

        if (closeModalBtn) {
            closeModalBtn.addEventListener("click", hideModal);
        }

        if (els.modal) {
            els.modal.addEventListener("click", function (event) {
                if (event.target === els.modal) {
                    hideModal();
                }
            });
        }
    });
})();
