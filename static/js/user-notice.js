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

    function lastCookie(name) {
        var parts = (document.cookie || "").split(";");
        var value = "";
        var prefix = name + "=";
        for (var i = 0; i < parts.length; i++) {
            var part = parts[i].trim();
            if (part.indexOf(prefix) === 0) {
                value = decodeURIComponent(part.slice(prefix.length));
            }
        }
        return value;
    }

    function csrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) {
            var metaToken = (meta.getAttribute("content") || "").trim();
            if (metaToken) {
                return metaToken;
            }
        }
        var hidden = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (hidden && hidden.value) {
            return hidden.value;
        }
        return lastCookie("kkcsrf") || lastCookie("csrftoken");
    }

    function reloadIfSessionExpired(data, response) {
        if (!response || response.status !== 403) {
            return false;
        }
        if (!data || data.code !== "AUTH_SESSION_EXPIRED") {
            return false;
        }
        try {
            if (sessionStorage.getItem("kk-csrf-reload")) {
                return false;
            }
            sessionStorage.setItem("kk-csrf-reload", "1");
        } catch (e) {
            return false;
        }
        window.location.reload();
        return true;
    }

    function notifyError(error, fallback) {
        show(messageFromError(error, fallback), "error");
    }

    function readJsonResponse(response) {
        return response.text().then(function (text) {
            var data = {};
            if (text && text.trim()) {
                try {
                    data = JSON.parse(text);
                } catch (e) {
                    throw new Error(NETWORK);
                }
            }
            if (!response.ok) {
                if (reloadIfSessionExpired(data, response)) {
                    return new Promise(function () {});
                }
                throw new Error(data.error || GENERIC);
            }
            try {
                sessionStorage.removeItem("kk-csrf-reload");
            } catch (e) {}
            return data;
        });
    }

    window.KokkorisNotice = {
        GENERIC: GENERIC,
        NETWORK: NETWORK,
        show: show,
        csrfToken: csrfToken,
        reloadIfSessionExpired: reloadIfSessionExpired,
        error: function (message) {
            show(message, "error");
        },
        success: function (message) {
            show(message, "success");
        },
        messageFromError: messageFromError,
        fromError: notifyError,
        readJsonResponse: readJsonResponse,
    };
})();
