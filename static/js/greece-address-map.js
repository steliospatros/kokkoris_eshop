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

    function getComponent(components, type, useShort) {
        var match = components.find(function (component) {
            return component.types.indexOf(type) !== -1;
        });
        if (!match) {
            return "";
        }
        return useShort ? match.short_name : match.long_name;
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
            updateCoords(location.lat(), location.lng());
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
            });
        }

        var addressAutocomplete = new google.maps.places.Autocomplete(addressInput, {
            componentRestrictions: { country: "gr" },
            fields: ["address_components", "formatted_address", "geometry", "place_id", "types"],
        });
        addressAutocomplete.bindTo("bounds", map);

        addressAutocomplete.addListener("place_changed", function () {
            var place = addressAutocomplete.getPlace();
            if (!place || !place.geometry || !place.geometry.location) {
                setHint("Επίλεξε μια διεύθυνση από τη λίστα.");
                return;
            }
            applyFromAddressSelection(place);
        });

        map.addListener("click", function (event) {
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
