# Οδηγίες σύνδεσης BOX NOW

Η παράδοση σε **BOX NOW locker** εμφανίζεται πάντα στο checkout (βήμα 2), μαζί με τις τιμές και τα όρια βάρους/διαστάσεων. Ο χάρτης locker και η αυτόματη δημιουργία voucher χρειάζονται τα κλειδιά του Partner API.

Προδιαγραφές που ακολουθεί ο κώδικας:

- OpenAPI **partner-api-1.68.yaml**
- **BoxNow API Manual v7.2** (auth, delivery-requests, labels)
- **Webhook-Based Parcel Tracking Guide v1.4.6**

## 1. Εγγραφή συνεργάτη

1. Επικοινώνησε με την BOX NOW: ict@boxnow.gr / sales@boxnow.gr
2. Θα λάβεις `partnerId`, `client_id` / `client_secret`, API URLs, `locationId` αποθήκης, και (για tracking) webhook secret.

## 2. Ρύθμιση `.env`

```env
BOXNOW_PARTNER_ID=123
BOXNOW_OAUTH_CLIENT_ID=...
BOXNOW_OAUTH_CLIENT_SECRET=...
BOXNOW_API_URL=https://api-stage.boxnow.gr
BOXNOW_LOCATION_API_URL=https://locationapi-stage.boxnow.gr
BOXNOW_ORIGIN_LOCATION_ID=8
BOXNOW_NOTIFY_EMAIL=orders@kokkorispetfood.gr
BOXNOW_ORIGIN_CONTACT_NAME=Kokkoris Pet Food
BOXNOW_ORIGIN_CONTACT_PHONE=+30210...
BOXNOW_ORIGIN_CONTACT_EMAIL=orders@kokkorispetfood.gr
BOXNOW_WEBHOOK_SECRET=...

# Τιμές ανά θήκη από το συμβόλαιό σου (€)
BOXNOW_FEE_SMALL=1.80
BOXNOW_FEE_MEDIUM=2.50
BOXNOW_FEE_LARGE=3.50
BOXNOW_MAX_WEIGHT_KG=20.0
```

Production URLs όταν είσαι έτοιμος:

```
BOXNOW_API_URL=https://api-production.boxnow.gr
BOXNOW_LOCATION_API_URL=https://locationapi-production.boxnow.gr
```

## 3. Έλεγχος

```bash
python manage.py migrate
python manage.py check_boxnow --latlng=37.9755,23.7348
```

## 4. Checkout — τρόπος αποστολής

Η επιλογή **«Παράδοση σε BOX NOW locker»** εμφανίζεται πάντα. Δείχνει:

- μέγεθος θήκης (1 μικρή / 2 μεσαία / 3 μεγάλη) από τις **επίσημες διαστάσεις locker**
- χρεώσιμο βάρος και όριο **20 kg**
- τιμή `BOXNOW_FEE_*` ή δωρεάν ≥ 60 €

Αν το δέμα δεν χωρά (βάρος > 20 kg ή διαστάσεις > 36×45×60 cm), η επιλογή γίνεται διάφανη/ανενεργή και εμφανίζεται μήνυμα να επιλεγεί courier.

Ο χάρτης (Map Widget v5) ανοίγει όταν υπάρχει `BOXNOW_PARTNER_ID`.

### Υπολογισμός θήκης

| Θήκη | compartmentSize | Εσωτερικές διαστάσεις |
|------|-----------------|------------------------|
| Μικρή | 1 | 8 × 45 × 60 cm |
| Μεσαία | 2 | 17 × 45 × 60 cm |
| Μεγάλη | 3 | 36 × 45 × 60 cm |

Κώδικας: `checkout/boxnow_pricing.py`.

### Πληρωμή

Για BOX NOW δεν επιτρέπεται αντικαταβολή — μόνο κάρτα (Stripe).

## 5. Partner API μετά την παραγγελία

1. `POST /api/v1/auth-sessions` (OAuth client credentials)
2. `POST /api/v1/delivery-requests` με `origin.locationId`, `destination.locationId`, `items[].compartmentSize`, `items[].weight` **σε kg** (API 1.68)
3. Αποθηκεύονται `boxnow_delivery_request_id` και `boxnow_parcel_id`

### Ετικέτα

Admin → παραγγελία → ενέργεια **Εκτύπωση ετικέτας BOX NOW**:

```
GET /api/v1/parcels/{parcel_id}/label.pdf
```

## 6. Webhooks παρακολούθησης

Στο partner portal όρισε:

```
https://<domain>/checkout/boxnow/webhook/
```

Το endpoint δέχεται CloudEvents (`gr.boxnow.parcel_event_change`), επαληθεύει HMAC-SHA256 του raw `data` με `BOXNOW_WEBHOOK_SECRET`, και ενημερώνει `boxnow_last_event` / κατάσταση παραγγελίας (`delivered` → παραδόθηκε).

## 7. Αρχεία

| Αρχείο | Ρόλος |
|--------|-------|
| `checkout/delivery.py` | Επιλογές αποστολής + fee |
| `checkout/boxnow_pricing.py` | Θήκη, 20 kg, μηνύματα |
| `checkout/boxnow_client.py` | OAuth + delivery-requests + labels |
| `checkout/boxnow_webhooks.py` | Webhook events |
| `templates/checkout/delivery.html` | Map Widget v5 |
