(function () {
    "use strict";

    var modal = document.getElementById("auth-modal");
    if (!modal) {
        return;
    }

    var panels = {
        choice: document.getElementById("auth-panel-choice"),
        login: document.getElementById("auth-panel-login"),
        signup: document.getElementById("auth-panel-signup"),
        phone: document.getElementById("auth-panel-phone"),
        "reset-sent": document.getElementById("auth-panel-reset-sent"),
    };

    var phoneVerify = null;

    var loginForm = document.getElementById("auth-login-form");
    var signupForm = document.getElementById("auth-signup-form");
    var loginSubmit = document.getElementById("auth-login-submit");
    var signupSubmit = document.getElementById("auth-signup-submit");
    var googleLogin = document.getElementById("auth-google-login");
    var googleSignup = document.getElementById("auth-google-signup");

    var nextUrl = window.location.pathname + window.location.search;
    var googleOAuthReady = modal.dataset.googleOauthReady === "true";
    var googleBaseUrl = modal.dataset.googleLoginUrl || "/accounts/google/login/";

    function googleLoginUrl() {
        var separator = googleBaseUrl.indexOf("?") >= 0 ? "&" : "?";
        return googleBaseUrl + separator + "next=" + encodeURIComponent(nextUrl);
    }

    function isGoogleOAuthReady(button) {
        if (button && button.dataset.googleOauthReady === "false") {
            return false;
        }
        return googleOAuthReady;
    }

    function handleGoogleClick(event) {
        var button = event.currentTarget;
        if (!isGoogleOAuthReady(button)) {
            event.preventDefault();
            return;
        }
        event.preventDefault();
        window.location.href = googleLoginUrl();
    }

    function getCookie(name) {
        var match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
        return match ? decodeURIComponent(match[2]) : "";
    }

    function csrfToken() {
        return getCookie("csrftoken");
    }

    function switchToPanel(name) {
        clearErrors();
        if (name === "login") {
            var signupEmail = document.getElementById("auth-signup-email");
            var loginEmail = document.getElementById("auth-login-email");
            if (signupEmail && loginEmail && signupEmail.value.trim() && !loginEmail.value.trim()) {
                loginEmail.value = signupEmail.value.trim();
            }
            showPanel("login");
            if (loginEmail) {
                loginEmail.focus();
            }
            return;
        }
        if (name === "signup") {
            var loginEmailField = document.getElementById("auth-login-email");
            var signupEmailField = document.getElementById("auth-signup-email");
            if (loginEmailField && signupEmailField && loginEmailField.value.trim() && !signupEmailField.value.trim()) {
                signupEmailField.value = loginEmailField.value.trim();
            }
            showPanel("signup");
            if (signupEmailField) {
                signupEmailField.focus();
            }
        }
    }

    function showPanel(name) {
        Object.keys(panels).forEach(function (key) {
            if (panels[key]) {
                panels[key].classList.toggle("hidden", key !== name);
            }
        });
        clearErrors();
    }

    function clearErrors() {
        modal.querySelectorAll(".auth-field-error, .auth-form-error").forEach(function (el) {
            el.textContent = "";
            el.classList.add("hidden");
        });
        modal.querySelectorAll("input").forEach(function (input) {
            input.classList.remove("border-red-500");
        });
    }

    function showFieldErrors(formPrefix, errors) {
        Object.keys(errors).forEach(function (field) {
            var messages = errors[field];
            if (!messages || !messages.length) {
                return;
            }
            var text = messages.join(" ");

            if (field === "__all__") {
                var allError = document.getElementById("auth-" + formPrefix + "-form-error");
                if (allError) {
                    allError.textContent = text;
                    allError.classList.remove("hidden");
                }
                return;
            }

            var mapped = field;
            if (field === "login") {
                mapped = "email";
            }

            var errorEl = document.getElementById("auth-" + formPrefix + "-" + mapped + "-error");
            if (errorEl) {
                errorEl.textContent = text;
                errorEl.classList.remove("hidden");
                var input = document.getElementById("auth-" + formPrefix + "-" + mapped);
                if (input) {
                    input.classList.add("border-red-500");
                }
                return;
            }

            var formError = document.getElementById("auth-" + formPrefix + "-form-error");
            if (formError) {
                formError.textContent = text;
                formError.classList.remove("hidden");
            }
        });
    }

    function lockBody() {
        document.body.classList.add("auth-modal-open", "overflow-hidden");
    }

    function unlockBody() {
        document.body.classList.remove("auth-modal-open", "overflow-hidden");
    }

    function showModal(panel) {
        showPanel(panel || "choice");
        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
        lockBody();
        if (googleOAuthReady) {
            updateGoogleLinks();
        }
    }

    function hideModal() {
        modal.classList.add("hidden");
        modal.setAttribute("aria-hidden", "true");
        unlockBody();
        showPanel("choice");
        if (loginForm) {
            loginForm.reset();
        }
        if (signupForm) {
            signupForm.reset();
        }
        clearErrors();
    }

    function loginEmailValue() {
        var loginEmail = document.getElementById("auth-login-email");
        return loginEmail ? loginEmail.value.trim() : "";
    }

    function isValidEmail(value) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    }

    function requestPasswordReset() {
        var email = loginEmailValue();
        clearErrors();

        if (!email) {
            var emailError = document.getElementById("auth-login-email-error");
            if (emailError) {
                emailError.textContent = "Συμπλήρωσε πρώτα το email σου.";
                emailError.classList.remove("hidden");
            }
            var emailInput = document.getElementById("auth-login-email");
            if (emailInput) {
                emailInput.classList.add("border-red-500");
                emailInput.focus();
            }
            return;
        }

        if (!isValidEmail(email)) {
            var invalidError = document.getElementById("auth-login-email-error");
            if (invalidError) {
                invalidError.textContent = "Μη έγκυρο email.";
                invalidError.classList.remove("hidden");
            }
            return;
        }

        var showResetBtn = document.getElementById("auth-show-reset");
        if (showResetBtn) {
            showResetBtn.textContent = "Αποστολή…";
            showResetBtn.disabled = true;
        }

        postJson("/accounts/api/password/reset/", { email: email })
            .then(function (result) {
                if (result.ok && result.data.ok) {
                    var messageEl = document.getElementById("auth-reset-sent-message");
                    if (messageEl) {
                        messageEl.textContent = result.data.message || "";
                    }
                    showPanel("reset-sent");
                    return;
                }
                if (result.data.errors) {
                    showFieldErrors("login", result.data.errors);
                }
            })
            .catch(function () {
                var formError = document.getElementById("auth-login-form-error");
                if (formError) {
                    formError.textContent = "Κάτι πήγε στραβά. Δοκίμασε ξανά.";
                    formError.classList.remove("hidden");
                }
            })
            .finally(function () {
                if (showResetBtn) {
                    showResetBtn.textContent = "Ξέχασες τον κωδικό;";
                    showResetBtn.disabled = false;
                }
            });
    }

    function updateGoogleLinks() {
        if (!googleOAuthReady) {
            return;
        }
        var href = googleLoginUrl();
        if (googleLogin) {
            googleLogin.href = href;
        }
        if (googleSignup) {
            googleSignup.href = href;
        }
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
                return { ok: response.ok, status: response.status, data: data };
            });
        });
    }

    function handleAuthSuccess(data) {
        if (data.phone_verified === false) {
            if (!phoneVerify && window.kokkorisInitPhoneVerify) {
                phoneVerify = window.kokkorisInitPhoneVerify("auth", {
                    redirect: data.redirect || nextUrl,
                    onSuccess: function () {
                        hideModal();
                        if (data.redirect) {
                            window.location.href = data.redirect;
                        } else {
                            window.location.reload();
                        }
                    },
                });
            } else if (phoneVerify) {
                phoneVerify.setRedirect(data.redirect || nextUrl);
                phoneVerify.show();
            }
            showPanel("phone");
            return;
        }
        hideModal();
        if (data.redirect) {
            window.location.href = data.redirect;
        } else {
            window.location.reload();
        }
    }

    window.kokkorisOpenAuthModal = function (panel, redirectNext) {
        if (redirectNext) {
            nextUrl = redirectNext;
        } else {
            nextUrl = window.location.pathname + window.location.search;
        }
        showModal(panel || "choice");
    };

    document.addEventListener("DOMContentLoaded", function () {
        var showLoginBtn = document.getElementById("auth-show-login");
        var showSignupBtn = document.getElementById("auth-show-signup");
        var showResetBtn = document.getElementById("auth-show-reset");
        var resetBackLoginBtn = document.getElementById("auth-reset-back-login");

        if (showLoginBtn) {
            showLoginBtn.addEventListener("click", function () {
                showPanel("login");
                var emailInput = document.getElementById("auth-login-email");
                if (emailInput) {
                    emailInput.focus();
                }
            });
        }

        if (showSignupBtn) {
            showSignupBtn.addEventListener("click", function () {
                showPanel("signup");
                var emailInput = document.getElementById("auth-signup-email");
                if (emailInput) {
                    emailInput.focus();
                }
            });
        }

        if (showResetBtn) {
            showResetBtn.addEventListener("click", function () {
                requestPasswordReset();
            });
        }

        var loginEmailInput = document.getElementById("auth-login-email");
        if (loginEmailInput) {
            loginEmailInput.addEventListener("input", function () {
                var emailError = document.getElementById("auth-login-email-error");
                if (emailError && emailError.textContent) {
                    emailError.classList.add("hidden");
                    emailError.textContent = "";
                    loginEmailInput.classList.remove("border-red-500");
                }
            });
        }

        if (resetBackLoginBtn) {
            resetBackLoginBtn.addEventListener("click", function () {
                showPanel("login");
            });
        }

        var switchToSignupBtn = document.getElementById("auth-switch-to-signup");
        if (switchToSignupBtn) {
            switchToSignupBtn.addEventListener("click", function () {
                switchToPanel("signup");
            });
        }

        var switchToLoginBtn = document.getElementById("auth-switch-to-login");
        if (switchToLoginBtn) {
            switchToLoginBtn.addEventListener("click", function () {
                switchToPanel("login");
            });
        }

        if (googleLogin) {
            googleLogin.addEventListener("click", handleGoogleClick);
        }

        if (googleSignup) {
            googleSignup.addEventListener("click", handleGoogleClick);
        }

        var closeBtn = document.getElementById("auth-modal-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", hideModal);
        }

        modal.querySelectorAll(".auth-back-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                showPanel(btn.dataset.target || "choice");
            });
        });

        if (loginForm) {
            loginForm.addEventListener("submit", function (event) {
                event.preventDefault();
                clearErrors();
                if (loginSubmit) {
                    loginSubmit.disabled = true;
                }

                postJson("/accounts/api/login/", {
                    email: document.getElementById("auth-login-email").value.trim(),
                    password: document.getElementById("auth-login-password").value,
                    next: nextUrl,
                })
                    .then(function (result) {
                        if (result.ok && result.data.ok) {
                            handleAuthSuccess(result.data);
                            return;
                        }
                        if (result.data.errors) {
                            showFieldErrors("login", result.data.errors);
                        }
                    })
                    .catch(function () {
                        var formError = document.getElementById("auth-login-form-error");
                        if (formError) {
                            formError.textContent = "Κάτι πήγε στραβά. Δοκίμασε ξανά.";
                            formError.classList.remove("hidden");
                        }
                    })
                    .finally(function () {
                        if (loginSubmit) {
                            loginSubmit.disabled = false;
                        }
                    });
            });
        }

        if (signupForm) {
            signupForm.addEventListener("submit", function (event) {
                event.preventDefault();
                clearErrors();

                var password1Input = document.getElementById("auth-signup-password1");
                var password1Error = document.getElementById("auth-signup-password1-error");
                if (password1Input && password1Error && window.kokkorisPasswordRules) {
                    var passwordError = window.kokkorisPasswordRules.firstPasswordError(
                        password1Input.value
                    );
                    if (passwordError) {
                        password1Error.textContent = passwordError;
                        password1Error.classList.remove("hidden");
                        password1Input.classList.add("border-red-500");
                        password1Input.focus();
                        return;
                    }
                }

                if (signupSubmit) {
                    signupSubmit.disabled = true;
                }

                postJson("/accounts/api/signup/", {
                    email: document.getElementById("auth-signup-email").value.trim(),
                    password1: document.getElementById("auth-signup-password1").value,
                    password2: document.getElementById("auth-signup-password2").value,
                    next: nextUrl,
                })
                    .then(function (result) {
                        if (result.ok && result.data.ok) {
                            handleAuthSuccess(result.data);
                            return;
                        }
                        if (result.data.errors) {
                            showFieldErrors("signup", result.data.errors);
                        }
                    })
                    .catch(function () {
                        var formError = document.getElementById("auth-signup-form-error");
                        if (formError) {
                            formError.textContent = "Κάτι πήγε στραβά. Δοκίμασε ξανά.";
                            formError.classList.remove("hidden");
                        }
                    })
                    .finally(function () {
                        if (signupSubmit) {
                            signupSubmit.disabled = false;
                        }
                    });
            });
        }

        document.querySelectorAll("[data-auth-trigger]").forEach(function (trigger) {
            trigger.addEventListener("click", function (event) {
                event.preventDefault();
                var panel = trigger.dataset.authPanel || "choice";
                window.kokkorisOpenAuthModal(panel);
            });
        });

        if (panels.phone && window.kokkorisInitPhoneVerify) {
            phoneVerify = window.kokkorisInitPhoneVerify("auth", {
                redirect: nextUrl,
                onSuccess: function () {
                    hideModal();
                    window.location.href = nextUrl;
                },
            });
        }
    });
})();
