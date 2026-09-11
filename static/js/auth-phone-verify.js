(function () {
    "use strict";

    var SEND_URL = "/accounts/api/phone/send-otp/";
    var VERIFY_URL = "/accounts/api/phone/verify-otp/";
    var RESEND_SECONDS = 60;
    var OTP_TTL_SECONDS = 600;

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
            body: JSON.stringify(payload || {}),
        }).then(function (response) {
            var contentType = response.headers.get("content-type") || "";
            if (contentType.indexOf("application/json") === -1) {
                if (response.status === 403) {
                    throw new Error("Η συνεδρία έληξε. Ανανέωσε τη σελίδα και δοκίμασε ξανά.");
                }
                throw new Error("Κάτι πήγε στραβά. Δοκίμασε ξανά σε λίγο.");
            }
            return response.json().then(function (data) {
                return { ok: response.ok, status: response.status, data: data };
            });
        });
    }

    function digitsOnly(value) {
        return String(value || "").replace(/\D/g, "");
    }

    function formatPhoneDashed(digits) {
        digits = digitsOnly(digits).slice(0, 10);
        if (digits.length <= 2) {
            return digits;
        }
        if (digits.length <= 6) {
            return digits.slice(0, 2) + "-" + digits.slice(2);
        }
        return digits.slice(0, 2) + "-" + digits.slice(2, 6) + "-" + digits.slice(6);
    }

    function maskPhone(digits) {
        digits = digitsOnly(digits);
        if (digits.length < 4) {
            return formatPhoneDashed(digits);
        }
        return digits.slice(0, 2) + "**-****-**" + digits.slice(-2);
    }

    function setLoading(button, spinnerClass, labelClass, loading) {
        var spinner = button.querySelector("." + spinnerClass);
        var label = button.querySelector("." + labelClass);
        button.disabled = loading;
        if (spinner) {
            spinner.classList.toggle("hidden", !loading);
        }
        if (label) {
            label.classList.toggle("opacity-70", loading);
        }
    }

    function initPhoneVerify(prefix, options) {
        options = options || {};
        var redirectUrl = options.redirect || "";
        var onSuccess = options.onSuccess;

        var phoneStep = document.getElementById(prefix + "-phone-step");
        var otpStep = document.getElementById(prefix + "-otp-step");
        var phoneInput = document.getElementById(prefix + "-phone-input");
        var phoneError = document.getElementById(prefix + "-phone-error");
        var sendBtn = document.getElementById(prefix + "-phone-send");
        var otpSentTo = document.getElementById(prefix + "-otp-sent-to");
        var otpExpiry = document.getElementById(prefix + "-otp-expiry");
        var otpError = document.getElementById(prefix + "-otp-error");
        var verifyBtn = document.getElementById(prefix + "-otp-verify");
        var resendBtn = document.getElementById(prefix + "-otp-resend");
        var resendCountdown = document.getElementById(prefix + "-resend-countdown");
        var changeBtn = document.getElementById(prefix + "-otp-change");
        var otpCells = document.querySelectorAll("#" + prefix + "-otp-boxes .phone-verify-panel__otp-cell");

        if (!phoneInput || !sendBtn) {
            return;
        }

        var lockedPhone = "";
        var resendTimer = null;
        var expiryTimer = null;
        var verifying = false;

        function clearPhoneError() {
            phoneError.classList.add("hidden");
            phoneError.textContent = "";
            phoneInput.classList.remove("phone-verify-panel__phone-input--error");
        }

        function clearOtpError() {
            otpError.classList.add("hidden");
            otpError.textContent = "";
            otpCells.forEach(function (cell) {
                cell.classList.remove("phone-verify-panel__otp-cell--error");
            });
        }

        function showPhoneError(msg) {
            phoneError.textContent = msg;
            phoneError.classList.remove("hidden");
            phoneInput.classList.add("phone-verify-panel__phone-input--error");
        }

        function showOtpError(msg) {
            otpError.textContent = msg;
            otpError.classList.remove("hidden");
            otpCells.forEach(function (cell) {
                cell.classList.add("phone-verify-panel__otp-cell--error");
            });
        }

        function normalizePhoneInput() {
            if (phoneInput.readOnly) {
                return;
            }
            var digits = digitsOnly(phoneInput.value);
            if (digits.startsWith("30") && digits.length > 10) {
                digits = digits.slice(2);
            }
            if (digits.startsWith("0") && digits.length === 11) {
                digits = digits.slice(1);
            }
            phoneInput.value = formatPhoneDashed(digits.slice(0, 10));
        }

        function getPhoneDigits() {
            return digitsOnly(phoneInput.value).slice(0, 10);
        }

        function getOtpCode() {
            var code = "";
            otpCells.forEach(function (cell) {
                code += digitsOnly(cell.value).slice(0, 1);
            });
            return code;
        }

        function clearOtpCells() {
            otpCells.forEach(function (cell) {
                cell.value = "";
            });
        }

        function startResendCooldown() {
            if (resendTimer) {
                clearInterval(resendTimer);
            }
            var remaining = RESEND_SECONDS;
            resendBtn.disabled = true;
            resendCountdown.textContent = String(remaining);
            resendTimer = setInterval(function () {
                remaining -= 1;
                resendCountdown.textContent = String(Math.max(remaining, 0));
                if (remaining <= 0) {
                    clearInterval(resendTimer);
                    resendBtn.disabled = false;
                }
            }, 1000);
        }

        function startExpiryCountdown() {
            if (expiryTimer) {
                clearInterval(expiryTimer);
            }
            var remaining = OTP_TTL_SECONDS;
            function tick() {
                var mins = Math.floor(remaining / 60);
                var secs = remaining % 60;
                otpExpiry.textContent =
                    "Ο κωδικός λήγει σε " +
                    mins +
                    ":" +
                    (secs < 10 ? "0" : "") +
                    secs;
                remaining -= 1;
                if (remaining < 0) {
                    clearInterval(expiryTimer);
                    otpExpiry.textContent = "Ο κωδικός έληξε. Στείλε νέο SMS.";
                }
            }
            tick();
            expiryTimer = setInterval(tick, 1000);
        }

        function showOtpStep(phone) {
            lockedPhone = digitsOnly(phone) || getPhoneDigits();
            phoneInput.value = formatPhoneDashed(lockedPhone);
            phoneInput.readOnly = true;
            phoneInput.classList.add("phone-verify-panel__phone-input--locked");

            phoneStep.classList.add("hidden");
            otpStep.classList.remove("hidden");

            otpSentTo.innerHTML =
                "Στάλθηκε κωδικός στο <strong>" + maskPhone(lockedPhone) + "</strong>.";

            clearOtpCells();
            startResendCooldown();
            startExpiryCountdown();
            if (otpCells[0]) {
                otpCells[0].focus();
            }
        }

        function showPhoneStep() {
            if (resendTimer) {
                clearInterval(resendTimer);
            }
            if (expiryTimer) {
                clearInterval(expiryTimer);
            }
            lockedPhone = "";
            phoneInput.readOnly = false;
            phoneInput.classList.remove("phone-verify-panel__phone-input--locked");
            otpStep.classList.add("hidden");
            phoneStep.classList.remove("hidden");
            clearOtpError();
            clearOtpCells();
            phoneInput.focus();
        }

        function sendOtp() {
            clearPhoneError();
            clearOtpError();
            normalizePhoneInput();

            var digits = lockedPhone || getPhoneDigits();
            if (!digits) {
                showPhoneError("Συμπλήρωσε το κινητό.");
                phoneInput.focus();
                return;
            }

            setLoading(sendBtn, prefix + "-send-spinner", prefix + "-send-label", true);

            postJson(SEND_URL, { phone_number: digits })
                .then(function (result) {
                    if (!result.ok) {
                        showPhoneError(result.data.error || "Δεν στάλθηκε SMS.");
                        return;
                    }
                    showOtpStep(result.data.phone_number);
                })
                .catch(function (err) {
                    showPhoneError(err.message || "Η σύνδεση διακόπηκε. Έλεγξε το δίκτυό σου και δοκίμασε ξανά.");
                })
                .finally(function () {
                    setLoading(sendBtn, prefix + "-send-spinner", prefix + "-send-label", false);
                });
        }

        function verifyOtp() {
            if (verifying) {
                return;
            }

            clearOtpError();
            var code = getOtpCode();
            if (code.length !== 6) {
                showOtpError("6 ψηφία απαιτούνται.");
                return;
            }

            var phone = lockedPhone || getPhoneDigits();
            if (!phone) {
                showOtpError("Στείλε SMS πρώτα.");
                return;
            }

            verifying = true;
            setLoading(verifyBtn, prefix + "-verify-spinner", prefix + "-verify-label", true);

            postJson(VERIFY_URL, { phone_number: phone, code: code })
                .then(function (result) {
                    if (!result.ok) {
                        showOtpError(result.data.error || "Λάθος κωδικός.");
                        return;
                    }
                    if (typeof onSuccess === "function") {
                        onSuccess(result.data);
                        return;
                    }
                    if (redirectUrl) {
                        window.location.href = redirectUrl;
                    } else {
                        window.location.reload();
                    }
                })
                .catch(function (err) {
                    showOtpError(err.message || "Η σύνδεση διακόπηκε. Έλεγξε το δίκτυό σου και δοκίμασε ξανά.");
                })
                .finally(function () {
                    verifying = false;
                    setLoading(verifyBtn, prefix + "-verify-spinner", prefix + "-verify-label", false);
                });
        }

        phoneInput.addEventListener("input", normalizePhoneInput);

        sendBtn.addEventListener("click", sendOtp);

        verifyBtn.addEventListener("click", verifyOtp);

        resendBtn.addEventListener("click", function () {
            sendOtp();
        });

        changeBtn.addEventListener("click", showPhoneStep);

        otpCells.forEach(function (cell, index) {
            cell.addEventListener("input", function () {
                cell.value = digitsOnly(cell.value).slice(0, 1);
                cell.classList.remove("phone-verify-panel__otp-cell--error");
                if (cell.value && index < otpCells.length - 1) {
                    otpCells[index + 1].focus();
                }
                if (getOtpCode().length === 6) {
                    verifyOtp();
                }
            });

            cell.addEventListener("keydown", function (event) {
                if (event.key === "Backspace" && !cell.value && index > 0) {
                    otpCells[index - 1].focus();
                }
            });

            cell.addEventListener("paste", function (event) {
                event.preventDefault();
                var pasted = digitsOnly(
                    (event.clipboardData || window.clipboardData).getData("text")
                ).slice(0, 6);
                pasted.split("").forEach(function (digit, i) {
                    if (otpCells[i]) {
                        otpCells[i].value = digit;
                    }
                });
                if (pasted.length === 6) {
                    verifyOtp();
                } else if (otpCells[pasted.length]) {
                    otpCells[pasted.length].focus();
                }
            });
        });

        if (phoneInput.value) {
            phoneInput.value = formatPhoneDashed(phoneInput.value);
        }

        return {
            show: function () {
                showPhoneStep();
            },
            setRedirect: function (url) {
                redirectUrl = url;
            },
        };
    }

    window.kokkorisInitPhoneVerify = initPhoneVerify;

    document.addEventListener("DOMContentLoaded", function () {
        var standalone = document.getElementById("phone-verify-modal");
        if (standalone) {
            window.kokkorisPhoneVerifyModal = initPhoneVerify("pvm", {
                redirect: standalone.dataset.redirect || "",
            });
            if (standalone.dataset.autoOpen === "true") {
                standalone.classList.remove("hidden");
                standalone.setAttribute("aria-hidden", "false");
                document.body.classList.add("overflow-hidden");
            }
        }
    });
})();
