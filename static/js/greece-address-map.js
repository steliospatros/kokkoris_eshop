(function (window) {
    "use strict";

    var ATHENS_CENTER = { lat: 37.9838, lng: 23.7275 };
    var GREECE_BOUNDS = {
        north: 41.85,
        south: 34.45,
        west: 19.0,
        east: 29.75,
    };
    var ATHENS_URBAN_PREFIXES = ["10", "11", "12", "13", "14", "15", "16", "17", "18"];
    var AUTO_FIELDS = ["city", "area", "street", "street_number", "postal_code"];
    var GREEK_GEO_OPTIONS = { language: "el", region: "gr" };
    var PLACES_AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete";

    function getComponent(components, type, useShort) {
        var match = components.find(function (component) {
            return component.types && component.types.indexOf(type) !== -1;
        });
        if (!match) {
            return "";
        }
        if (useShort) {
            return match.short_name || match.shortText || "";
        }
        return match.long_name || match.longText || "";
    }

    function getComponentAny(components, types, useShort) {
        var i;
        for (i = 0; i < types.length; i++) {
            var value = getComponent(components, types[i], useShort);
            if (value) {
                return value;
            }
        }
        return "";
    }

    function normalizePostal(postal) {
        return (postal || "").replace(/\s/g, "");
    }

    function isAthensUrbanPostcode(postal) {
        var pc = normalizePostal(postal);
        if (pc.length < 2) {
            return false;
        }
        return ATHENS_URBAN_PREFIXES.indexOf(pc.substring(0, 2)) !== -1;
    }

    function parseAddressComponents(components) {
        var postalCode = normalizePostal(getComponent(components, "postal_code"));
        var locality = getComponent(components, "locality");
        var sublocality = getComponentAny(components, [
            "sublocality",
            "sublocality_level_1",
            "neighborhood",
        ]);
        var admin3 = getComponent(components, "administrative_area_level_3");
        var route = getComponent(components, "route");
        var streetNumber = getComponent(components, "street_number");
        var city;
        var area;

        if (isAthensUrbanPostcode(postalCode)) {
            city = "Αθήνα";
            area = locality || sublocality || admin3;
        } else {
            city =
                locality ||
                admin3 ||
                getComponent(components, "administrative_area_level_2") ||
                "";
            area = sublocality || admin3 || locality;
        }

        var streetLine = route
            ? streetNumber
                ? route + " " + streetNumber
                : route
            : "";

        return {
            city: city,
            area: area,
            street: route,
            street_number: streetNumber,
            postal_code: postalCode,
            address: streetLine,
        };
    }

    function isInGreece(components) {
        return getComponent(components, "country", true) === "GR";
    }

    function setInputValue(input, value) {
        if (!input) {
            return;
        }
        input.value = value || "";
        input.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function hiddenInput(fieldName) {
        return document.getElementById("id_" + fieldName);
    }

    function displayInput(fieldName) {
        return document.getElementById("id_" + fieldName + "_display");
    }

    function discoverApiKey(explicitKey) {
        if (explicitKey) {
            return explicitKey;
        }
        var scripts = document.querySelectorAll('script[src*="maps.googleapis.com/maps/api/js"]');
        for (var i = 0; i < scripts.length; i++) {
            var match = scripts[i].src.match(/[?&]key=([^&]+)/);
            if (match && match[1]) {
                return decodeURIComponent(match[1]);
            }
        }
        return "";
    }

    function ensureDropdownStyles() {
        if (document.getElementById("kokkoris-places-ac-styles")) {
            return;
        }
        var style = document.createElement("style");
        style.id = "kokkoris-places-ac-styles";
        style.textContent =
            ".kokkoris-places-dropdown{position:absolute;left:0;right:0;top:calc(100% + 4px);z-index:1050;" +
            "background:#fff;border:1px solid #cbd5e1;border-radius:0.75rem;box-shadow:0 12px 28px rgba(15,23,42,.12);" +
            "max-height:17rem;overflow-y:auto;margin:0;padding:0.25rem 0;list-style:none;}" +
            ".kokkoris-places-dropdown.hidden{display:none;}" +
            ".kokkoris-places-item{padding:0.55rem 0.85rem;cursor:pointer;font-family:Inter,sans-serif;" +
            "font-size:0.875rem;line-height:1.35;color:#1e293b;border-bottom:1px solid #f1f5f9;}" +
            ".kokkoris-places-item:last-child{border-bottom:0;}" +
            ".kokkoris-places-item:hover,.kokkoris-places-item.is-active{background:#f0fdfa;color:#115e59;}" +
            ".kokkoris-places-item__main{font-weight:600;display:block;}" +
            ".kokkoris-places-item__sub{font-size:0.75rem;color:#64748b;display:block;margin-top:1px;}";
        document.head.appendChild(style);
    }

    window.kokkorisInitGreeceAddressMap = function (config) {
        if (!window.google || !google.maps) {
            return;
        }

        var mapEl = document.getElementById(config.mapId);
        var addressInput = document.getElementById(config.addressInputId);
        var latInput = document.getElementById(config.latInputId);
        var lngInput = document.getElementById(config.lngInputId);
        var placeIdInput = document.getElementById(config.placeIdInputId);
        var componentsInput = document.getElementById(config.componentsInputId);
        var hintEl = document.getElementById(config.hintId);
        var apiKey = discoverApiKey(config.apiKey);

        if (!mapEl || !addressInput) {
            if (hintEl) {
                hintEl.textContent = "Δεν βρέθηκε το στοιχείο του χάρτη στη σελίδα.";
            }
            return;
        }

        var geocoder = new google.maps.Geocoder();
        var marker = null;
        var syncingFields = false;
        var ignoreAddressInputUntil = 0;

        function roundCoord(value) {
            if (value === "" || value === null || value === undefined) {
                return "";
            }
            return Number(value).toFixed(6);
        }

        function lockAddressInput() {
            ignoreAddressInputUntil = Date.now() + 800;
        }

        function shouldIgnoreAddressInput() {
            return syncingFields || Date.now() < ignoreAddressInputUntil;
        }

        var map = new google.maps.Map(mapEl, {
            center: ATHENS_CENTER,
            zoom: 12,
            restriction: {
                latLngBounds: GREECE_BOUNDS,
                strictBounds: false,
            },
            streetViewControl: false,
            mapTypeControl: false,
            fullscreenControl: false,
        });

        function setHint(message) {
            if (hintEl) {
                hintEl.textContent = message;
            }
        }

        function updateCoords(lat, lng) {
            if (latInput) {
                latInput.value =
                    lat === "" || lat === null || lat === undefined ? "" : roundCoord(lat);
            }
            if (lngInput) {
                lngInput.value =
                    lng === "" || lng === null || lng === undefined ? "" : roundCoord(lng);
            }
        }

        function updatePlaceId(placeId) {
            if (placeIdInput) {
                placeIdInput.value = placeId || "";
            }
        }

        function updateComponentsJson(components) {
            if (componentsInput) {
                componentsInput.value = components ? JSON.stringify(components) : "";
            }
        }

        function notifyChange() {
            if (typeof config.onFieldsUpdated === "function") {
                config.onFieldsUpdated();
            }
        }

        function setAutoField(fieldName, value) {
            setInputValue(hiddenInput(fieldName), value);
            var display = displayInput(fieldName);
            if (display) {
                display.value = value || "";
            }
        }

        function applyParsedFields(parsed) {
            syncingFields = true;
            AUTO_FIELDS.forEach(function (fieldName) {
                setAutoField(fieldName, parsed[fieldName] || "");
            });
            setInputValue(hiddenInput("address"), parsed.address || "");
            syncingFields = false;
        }

        function clearAutoFields() {
            syncingFields = true;
            AUTO_FIELDS.forEach(function (fieldName) {
                setAutoField(fieldName, "");
            });
            setInputValue(hiddenInput("address"), "");
            updateComponentsJson(null);
            syncingFields = false;
        }

        function validateGreece(result) {
            if (!result || !result.address_components || !isInGreece(result.address_components)) {
                setHint("Η τοποθεσία πρέπει να βρίσκεται εντός Ελλάδας.");
                return false;
            }
            if (!result.geometry || !result.geometry.location) {
                setHint("Δεν βρέθηκε έγκυρη τοποθεσία.");
                return false;
            }
            return true;
        }

        function applyParsedLocation(result, parsed) {
            syncingFields = true;
            lockAddressInput();
            applyParsedFields(parsed);
            updateComponentsJson(result.address_components);

            var location = result.geometry.location;
            var lat = typeof location.lat === "function" ? location.lat() : location.lat;
            var lng = typeof location.lng === "function" ? location.lng() : location.lng;
            updateCoords(lat, lng);
            updatePlaceId(result.place_id || "");
            ensureMarker(location);
            map.panTo(location);
            map.setZoom(16);
            syncingFields = false;

            if (!parsed.postal_code) {
                setHint("Επίλεξε πιο συγκεκριμένη διεύθυνση — δεν βρέθηκε Τ.Κ.");
            } else if (!parsed.street) {
                setHint("Δεν βρέθηκε δρόμος — επίλεξε πιο συγκεκριμένη διεύθυνση.");
            } else {
                setHint("Τα στοιχεία διεύθυνσης συμπληρώθηκαν και θα αποθηκευτούν δομημένα.");
            }
            notifyChange();
            return true;
        }

        function ensureMarker(position) {
            if (!marker) {
                marker = new google.maps.Marker({
                    map: map,
                    position: position,
                    draggable: true,
                });
                marker.addListener("dragend", function () {
                    reverseGeocode(marker.getPosition());
                });
            } else {
                marker.setPosition(position);
                marker.setMap(map);
            }
        }

        function applyFromMapResult(result) {
            if (!validateGreece(result)) {
                return false;
            }

            var parsed = parseAddressComponents(result.address_components);
            if (!parsed.address && result.formatted_address) {
                parsed.address = result.formatted_address.split(",")[0];
                if (!parsed.street) {
                    parsed.street = parsed.address;
                }
            }

            return applyParsedLocation(result, parsed);
        }

        function applyFromAddressSelection(result) {
            if (!validateGreece(result)) {
                return false;
            }

            var parsed = parseAddressComponents(result.address_components);
            syncingFields = true;
            lockAddressInput();
            if (parsed.address) {
                addressInput.value = parsed.address;
            } else if (result.formatted_address) {
                addressInput.value = result.formatted_address.split(",")[0];
            }
            syncingFields = false;

            return applyParsedLocation(result, parsed);
        }

        function reverseGeocode(latLng) {
            geocoder.geocode(
                Object.assign({ location: latLng }, GREEK_GEO_OPTIONS),
                function (results, status) {
                    if (status !== "OK" || !results || !results.length) {
                        setHint("Δεν βρέθηκε έγκυρη διεύθυνση για αυτό το σημείο.");
                        return;
                    }
                    applyFromMapResult(results[0]);
                }
            );
        }

        function selectByPlaceIdOrAddress(item) {
            var req = item.placeId
                ? Object.assign({ placeId: item.placeId }, GREEK_GEO_OPTIONS)
                : Object.assign(
                    { address: item.fullText, componentRestrictions: { country: "GR" } },
                    GREEK_GEO_OPTIONS
                );
            geocoder.geocode(req, function (results, status) {
                if (status === "OK" && results && results.length) {
                    applyFromAddressSelection(results[0]);
                } else if (item.fullText) {
                    geocoder.geocode(
                        Object.assign(
                            { address: item.fullText, componentRestrictions: { country: "GR" } },
                            GREEK_GEO_OPTIONS
                        ),
                        function (fallbackResults, fallbackStatus) {
                            if (fallbackStatus === "OK" && fallbackResults && fallbackResults.length) {
                                applyFromAddressSelection(fallbackResults[0]);
                            } else {
                                setHint("Επίλεξε μια διεύθυνση από τη λίστα.");
                            }
                        }
                    );
                } else {
                    setHint("Επίλεξε μια διεύθυνση από τη λίστα.");
                }
            });
        }

        // Autocomplete powered by Places API (New) + Geocoder fallback — never calls
        // legacy google.maps.places.Autocomplete, which triggers the Google error modal
        // when Legacy Places API is disabled on newer Google Cloud projects.
        ensureDropdownStyles();
        var parent = addressInput.parentElement;
        if (parent && window.getComputedStyle(parent).position === "static") {
            parent.style.position = "relative";
        }
        addressInput.setAttribute("autocomplete", "off");

        var dropdown = document.createElement("ul");
        dropdown.className = "kokkoris-places-dropdown hidden";
        dropdown.setAttribute("role", "listbox");
        if (parent) {
            parent.appendChild(dropdown);
        }

        var currentItems = [];
        var activeIndex = -1;
        var debounceTimer = null;
        var fetchSeq = 0;

        function hideDropdown() {
            dropdown.classList.add("hidden");
            dropdown.innerHTML = "";
            currentItems = [];
            activeIndex = -1;
        }

        function renderSuggestions(items) {
            dropdown.innerHTML = "";
            currentItems = items || [];
            activeIndex = -1;
            if (!currentItems.length) {
                dropdown.classList.add("hidden");
                return;
            }
            currentItems.forEach(function (item, idx) {
                var li = document.createElement("li");
                li.className = "kokkoris-places-item";
                li.setAttribute("role", "option");
                var main = document.createElement("span");
                main.className = "kokkoris-places-item__main";
                main.textContent = item.mainText || item.fullText;
                li.appendChild(main);
                if (item.secondaryText) {
                    var sub = document.createElement("span");
                    sub.className = "kokkoris-places-item__sub";
                    sub.textContent = item.secondaryText;
                    li.appendChild(sub);
                }
                li.addEventListener("mousedown", function (e) {
                    e.preventDefault();
                    hideDropdown();
                    selectByPlaceIdOrAddress(item);
                });
                li.addEventListener("mouseenter", function () {
                    setActive(idx);
                });
                dropdown.appendChild(li);
            });
            dropdown.classList.remove("hidden");
        }

        function setActive(idx) {
            var nodes = dropdown.querySelectorAll(".kokkoris-places-item");
            nodes.forEach(function (node, i) {
                node.classList.toggle("is-active", i === idx);
            });
            activeIndex = idx;
        }

        function fallbackGeocodeSuggestions(query, seq) {
            geocoder.geocode(
                Object.assign(
                    { address: query, componentRestrictions: { country: "GR" } },
                    GREEK_GEO_OPTIONS
                ),
                function (results, status) {
                    if (seq !== fetchSeq) {
                        return;
                    }
                    if (status !== "OK" || !results || !results.length) {
                        hideDropdown();
                        return;
                    }
                    var items = results.slice(0, 5).map(function (r) {
                        var parts = (r.formatted_address || "").split(",");
                        return {
                            placeId: r.place_id || "",
                            mainText: (parts[0] || r.formatted_address || "").trim(),
                            secondaryText: parts.slice(1).join(",").trim(),
                            fullText: r.formatted_address || query,
                        };
                    });
                    renderSuggestions(items);
                }
            );
        }

        function fetchSuggestions(query) {
            var seq = ++fetchSeq;
            if (!apiKey || !window.fetch) {
                fallbackGeocodeSuggestions(query, seq);
                return;
            }
            var center = map.getCenter() || ATHENS_CENTER;
            var lat = typeof center.lat === "function" ? center.lat() : center.lat;
            var lng = typeof center.lng === "function" ? center.lng() : center.lng;
            window
                .fetch(PLACES_AUTOCOMPLETE_URL, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": apiKey,
                    },
                    body: JSON.stringify({
                        input: query,
                        languageCode: "el",
                        regionCode: "gr",
                        includedRegionCodes: ["gr"],
                        locationBias: {
                            circle: {
                                center: { latitude: lat, longitude: lng },
                                radius: 50000.0,
                            },
                        },
                    }),
                })
                .then(function (resp) {
                    if (!resp.ok) {
                        throw new Error("places_http_" + resp.status);
                    }
                    return resp.json();
                })
                .then(function (data) {
                    if (seq !== fetchSeq) {
                        return;
                    }
                    var suggestions = (data && data.suggestions) || [];
                    var items = [];
                    suggestions.forEach(function (s) {
                        var p = s && s.placePrediction;
                        if (!p) {
                            return;
                        }
                        var full = (p.text && p.text.text) || "";
                        var sf = p.structuredFormat || {};
                        var main = (sf.mainText && sf.mainText.text) || full;
                        var sub = (sf.secondaryText && sf.secondaryText.text) || "";
                        if (full || main) {
                            items.push({
                                placeId: p.placeId || "",
                                mainText: main,
                                secondaryText: sub,
                                fullText: full || main,
                            });
                        }
                    });
                    if (items.length) {
                        renderSuggestions(items);
                    } else {
                        fallbackGeocodeSuggestions(query, seq);
                    }
                })
                .catch(function () {
                    if (seq === fetchSeq) {
                        fallbackGeocodeSuggestions(query, seq);
                    }
                });
        }

        map.addListener("click", function (event) {
            hideDropdown();
            reverseGeocode(event.latLng);
        });

        addressInput.addEventListener("input", function () {
            if (shouldIgnoreAddressInput()) {
                return;
            }
            updatePlaceId("");
            updateCoords("", "");
            clearAutoFields();
            if (marker) {
                marker.setMap(null);
            }
            setHint("Επίλεξε διεύθυνση από τη λίστα ή τοποθέτησε κουκίδα στον χάρτη.");
            notifyChange();

            if (debounceTimer) {
                window.clearTimeout(debounceTimer);
            }
            var q = (addressInput.value || "").trim();
            if (q.length < 2) {
                hideDropdown();
                return;
            }
            debounceTimer = window.setTimeout(function () {
                fetchSuggestions(q);
            }, 220);
        });

        addressInput.addEventListener("keydown", function (event) {
            if (dropdown.classList.contains("hidden") || !currentItems.length) {
                if (event.key === "Enter") {
                    var q = (addressInput.value || "").trim();
                    if (q.length >= 3 && (!latInput || !latInput.value)) {
                        event.preventDefault();
                        selectByPlaceIdOrAddress({ placeId: "", fullText: q });
                    }
                }
                return;
            }
            if (event.key === "ArrowDown") {
                event.preventDefault();
                setActive((activeIndex + 1) % currentItems.length);
            } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActive((activeIndex - 1 + currentItems.length) % currentItems.length);
            } else if (event.key === "Enter") {
                event.preventDefault();
                var chosen = currentItems[activeIndex >= 0 ? activeIndex : 0];
                hideDropdown();
                if (chosen) {
                    selectByPlaceIdOrAddress(chosen);
                }
            } else if (event.key === "Escape") {
                hideDropdown();
            }
        });

        addressInput.addEventListener("blur", function () {
            window.setTimeout(hideDropdown, 180);
        });

        var initialLat = parseFloat(config.initialLat);
        var initialLng = parseFloat(config.initialLng);
        if (!isNaN(initialLat) && !isNaN(initialLng)) {
            var saved = { lat: initialLat, lng: initialLng };
            updateCoords(saved.lat, saved.lng);
            map.setCenter(saved);
            map.setZoom(16);
            ensureMarker(saved);
            if (config.initialPlaceId) {
                updatePlaceId(config.initialPlaceId);
            }
        } else {
            map.setCenter(ATHENS_CENTER);
            map.setZoom(12);
            setHint(
                "Αναζήτησε διεύθυνση ή επίλεξε σημείο στον χάρτη — πόλη, περιοχή, δρόμος και Τ.Κ. συμπληρώνονται αυτόματα."
            );
        }
    };
})(window);
