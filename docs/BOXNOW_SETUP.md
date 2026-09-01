# Οδηγίες σύνδεσης BOX NOW

Αυτός ο οδηγός περιγράφει πώς να ενεργοποιήσεις την παράδοση σε **BOX NOW locker** στο e-shop Kokkoris.

## 1. Εγγραφή συνεργάτη

1. Επικοινώνησε με την BOX NOW για partner account:
   - **Email:** ict@boxnow.gr ή sales@boxnow.gr
   - **Docs:** https://boxnow.gr/en/partner-api
2. Θα λάβεις:
   - `partnerId` (για το Map Widget)
   - `client_id` / `client_secret` (OAuth 2.0)
   - `API_URL` (staging + production)
   - `locationId` του warehouse σου (σημείο παραλαβής δεμάτων)

## 2. Ρύθμιση `.env`

Αντίγραψε τις τιμές στο `.env` (δες `.env.example`):

```env
# Widget (υποχρεωτικό για εμφάνιση επιλογής στο checkout)
BOXNOW_PARTNER_ID=123

# Partner API (υποχρεωτικό για αυτόματη δημιουργία voucher μετά την παραγγελία)
BOXNOW_OAUTH_CLIENT_ID=...
BOXNOW_OAUTH_CLIENT_SECRET=...

# Staging (δοκιμές)
BOXNOW_API_URL=https://api-stage.boxnow.gr
BOXNOW_LOCATION_API_URL=https://locationapi-stage.boxnow.gr

# Production (όταν είσαι έτοιμος)
# BOXNOW_API_URL=https://api-production.boxnow.gr
# BOXNOW_LOCATION_API_URL=https://locationapi-production.boxnow.gr

BOXNOW_ORIGIN_LOCATION_ID=8
BOXNOW_NOTIFY_EMAIL=orders@kokkorispetfood.gr
BOXNOW_ORIGIN_CONTACT_NAME=Kokkoris Pet Food
BOXNOW_ORIGIN_CONTACT_PHONE=+30210...
BOXNOW_ORIGIN_CONTACT_EMAIL=orders@kokkorispetfood.gr

# Τιμές αποστολής ανά θήκη locker (€) — προσάρμοσε στο συμβόλαιό σου
BOXNOW_FEE_SMALL=1.80
BOXNOW_FEE_MEDIUM=2.50
BOXNOW_FEE_LARGE=3.50
BOXNOW_SMALL_MAX_KG=4.0
BOXNOW_MEDIUM_MAX_KG=10.0
```

## 3. Migration & έλεγχος

```bash
python manage.py migrate orders
python manage.py check_boxnow --latlng=37.9755,23.7348
```

Το `check_boxnow` ελέγχει OAuth και εμφανίζει κοντινά lockers.

## 4. Πώς λειτουργεί στο checkout

### Βήμα 2 — Τρόπος αποστολής

- Εμφανίζεται η επιλογή **«Παράδοση σε BOX NOW locker»** όταν έχει οριστεί `BOXNOW_PARTNER_ID`.
- Ο πελάτης πατά **«Επιλογή locker BOX NOW»** → ανοίγει το επίσημο Map Widget (popup).
- Μετά την επιλογή, αποθηκεύονται `locker id`, όνομα και διεύθυνση.

### Υπολογισμός κόστους

Ο αλγόριθμος βρίσκεται στο `checkout/boxnow_pricing.py`:

| Βήμα | Λογική |
|------|--------|
| Βάρος | Υπολογίζεται το chargeable weight (max πραγματικό vs όγκομετρικό) |
| Θήκη locker | ≤ `BOXNOW_SMALL_MAX_KG` → Μικρή (1), ≤ `BOXNOW_MEDIUM_MAX_KG` → Μεσαία (2), αλλιώς Μεγάλη (3) |
| Διαθεσιμότητα | Αν βάρος > `BOXNOW_MAX_WEIGHT_KG` (default 10 kg), η επιλογή BOX NOW απενεργοποιείται |
| Τιμή | `BOXNOW_FEE_SMALL` / `MEDIUM` / `LARGE` |
| Δωρεάν αποστολή | Παραγγελίες ≥ `FREE_SHIPPING_ORDER_MINIMUM` (default **60€**) |

### Βήμα 3 — Πληρωμή

- Για BOX NOW **δεν επιτρέπεται αντικαταβολή** — μόνο κάρτα (Stripe).

## 5. Partner API — ροή μετά την παραγγελία

Όταν ολοκληρωθεί η παραγγελία με `delivery_method=box_now` και το API είναι ρυθμισμένο:

1. `POST /api/v1/auth-sessions` → Bearer token
2. `POST /api/v1/delivery-requests` με:
   - `origin.locationId` = warehouse σου
   - `destination.locationId` = locker που επέλεξε ο πελάτης
   - `items[].compartmentSize` = 1/2/3
   - `paymentMode` = `prepaid`
3. Αποθηκεύονται `boxnow_delivery_request_id` και `boxnow_parcel_id` στην παραγγελία.

Κώδικας: `checkout/boxnow_client.py`, `checkout/boxnow_service.py`.

### Εκτύπωση label

```
GET /api/v1/parcels/{parcel_id}/label.pdf
```

ή μαζικά:

```
GET /api/v1/delivery-requests/{orderNumber}/label.pdf
```

## 6. Webhooks παρακολούθησης (προαιρετικά)

Η BOX NOW υποστηρίζει webhooks για status updates (π.χ. παραλαβή από locker).
Δες το **Webhook-Based Parcel Tracking Guide** που σου έδωσαν.

Για να τα ενεργοποιήσεις στο μέλλον, θα χρειαστεί endpoint στο Django + URL στο partner portal.

## 7. Αρχεία που άλλαξαν

| Αρχείο | Ρόλος |
|--------|-------|
| `checkout/delivery.py` | Επιλογές αποστολής + κεντρικός υπολογισμός fee |
| `checkout/boxnow_pricing.py` | Θήκη locker + τιμολόγηση |
| `checkout/boxnow_client.py` | OAuth + delivery-requests API |
| `templates/checkout/delivery.html` | Map Widget v5 |
| `orders/models.py` | Πεδία locker + parcel id |
| `core/settings.py` | Env variables |

## 8. Troubleshooting

| Πρόβλημα | Λύση |
|----------|------|
| Δεν εμφανίζεται η επιλογή BOX NOW | Βάλε `BOXNOW_PARTNER_ID` στο `.env` και κάνε restart server |
| Widget δεν ανοίγει | Έλεγξε `partnerId`, ad-blockers, console errors |
| API auth fails | Έλεγξε `client_id`/`secret` και staging vs production URL |
| `P406 Invalid compartment size` | Το καλάθι χρειάζεται μεγαλύτερη θήκη — έλεγξε βάρη προϊόντων στο admin |
| Δεν δημιουργείται voucher | Τρέξε `python manage.py check_boxnow` — χρειάζεται `BOXNOW_ORIGIN_LOCATION_ID` |
