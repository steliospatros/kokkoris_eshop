(function () {
    "use strict";

    var GENERIC = "Κάτι πήγε στραβά. Δοκίμασε ξανά σε λίγο.";
    var NETWORK = "Η σύνδεση διακόπηκε. Έλεγξε το δίκτυό σου και δοκίμασε ξανά.";
    var host = null;

    function ensureHost() {
        if (host) {
            return host;
        }
        host = document.createElement("div");
        host.id = "kokkoris-notice-host";
        host.setAttribute("aria-live", "polite");
        host.className = "kokkoris-notice-host";
        document.body.appendChild(host);
        return host;
    }

    function show(message, kind) {
        var text = (message || "").toString().trim();
        if (!text) {
            return;
        }
        var box = document.createElement("div");
        box.className = "kokkoris-notice kokkoris-notice--" + (kind === "success" ? "success" : "error");
        box.setAttribute("role", "status");
        box.textContent = text;
        ensureHost().appendChild(box);
        window.setTimeout(function () {
            box.classList.add("is-leaving");
            window.setTimeout(function () {
                if (box.parentNode) {
                    box.parentNode.removeChild(box);
                }
            }, 280);
        }, 5200);
    }

    function messageFromError(error, fallback) {
        var text = error && error.message ? String(error.message).trim() : "";
        if (!text || /failed to fetch|networkerror|load failed|unexpected token|json/i.test(text)) {
            return fallback || NETWORK;
        }
        return text;
    }

    function notifyError(error, fallback) {
        show(messageFromError(error, fallback), "error");
    }

    window.KokkorisNotice = {
        GENERIC: GENERIC,
        NETWORK: NETWORK,
        show: show,
        error: function (message) {
            show(message, "error");
        },
        success: function (message) {
            show(message, "success");
        },
        messageFromError: messageFromError,
        fromError: notifyError,
    };
})();
