# SCRIPTS.md — Όλα τα Scripts / Management Commands του project

Αυτό το αρχείο τεκμηριώνει **κάθε script / εντολή** που έχουμε φτιάξει ή χρησιμοποιούμε στο
project, με σκοπό, παραμέτρους, και ακριβή εντολή εκτέλεσης. Δες το [`README.md`](README.md)
για το "γιατί" πίσω από κάθε κομμάτι.

Πριν τρέξεις οτιδήποτε, πάντα ενεργοποίησε πρώτα το virtual environment:

```bash
cd ~/kokkoris_eshop
source venv/bin/activate
```

---

## 1. Ενσωματωμένες εντολές Django (`manage.py`)

### `runserver` — Εκκίνηση του development server

```bash
python manage.py runserver
```

Ανοίγει το site στο `http://127.0.0.1:8000/` και το Admin panel στο
`http://127.0.0.1:8000/admin/`. Τρέχει μόνο τοπικά, όχι για production χρήση.

### `makemigrations` — Δημιουργία νέου migration αρχείου

```bash
python manage.py makemigrations
```

Τρέχεις αυτό **κάθε φορά** που αλλάζεις κάτι στο `products/models.py` (νέο πεδίο, νέο model,
κλπ.). Δημιουργεί ένα αρχείο μέσα στο `products/migrations/` που περιγράφει την αλλαγή, αλλά
**δεν** την εφαρμόζει ακόμα στη βάση.

### `migrate` — Εφαρμογή migrations στη βάση

```bash
python manage.py migrate
```

Εφαρμόζει όλα τα εκκρεμή migrations πάνω στην πραγματική βάση δεδομένων (`db.sqlite3`),
δημιουργώντας/τροποποιώντας τους αντίστοιχους πίνακες.

### `createsuperuser` — Δημιουργία λογαριασμού διαχειριστή

```bash
python manage.py createsuperuser
```

Δημιουργεί έναν χρήστη με πλήρη δικαιώματα, ώστε να μπορείς να συνδεθείς στο `/admin/`.

> **Ενημέρωση (Part 2):** Μετά την προσθήκη του custom `CustomUser` model, ο λογαριασμός δεν έχει
> πλέον `username` — η εντολή θα σου ζητήσει μόνο **email** και **password**. Ο τρέχων superuser
> είναι `admin@kokkoriseshop.local` / `admin12345` (δες README ενότητα 11.7).
>
> Μπορείς επίσης να τον φτιάξεις χωρίς interactive prompts (χρήσιμο σε setup scripts):
>
> ```bash
> DJANGO_SUPERUSER_EMAIL=admin@kokkoriseshop.local DJANGO_SUPERUSER_PASSWORD=admin12345 \
>   python manage.py createsuperuser --noinput
> ```

### `shell` — Διαδραστικό Python κέλυφος με φορτωμένο το Django

```bash
python manage.py shell
```

Ανοίγει ένα Python REPL μέσα στο οποίο μπορείς να κάνεις queries απευθείας στη βάση, π.χ.:

```python
from products.models import Product
Product.objects.filter(company__name="CLUB4PAWS").count()
```

Μπορείς επίσης να τρέξεις μια εντολή inline χωρίς να μπεις σε interactive mode:

```bash
python manage.py shell -c "from products.models import Product; print(Product.objects.count())"
```

---

## 2. Custom Management Command: `seed_data`

**Αρχείο:** `products/management/commands/seed_data.py`

**Σκοπός:** Γεμίζει τη βάση με τα βασικά δεδομένα αναφοράς που χρειάζονται πριν μπορέσουμε να
εισάγουμε προϊόντα: `AnimalType` (Dog, Cat), `Category` (Dry Food, Canned Food, Sachets,
Litter, Bundle), `Company` (Core, CLUB4PAWS, OWNAT, PROFINE, EVERCLEAN, Wild Side, Puro Instinto).

**Είναι idempotent** — μπορείς να το τρέξεις όσες φορές θέλεις, δεν δημιουργεί διπλότυπα
(χρησιμοποιεί `get_or_create()` εσωτερικά).

### Εκτέλεση

```bash
python manage.py seed_data
```

Δεν χρειάζεται καμία παράμετρος. Στο τέλος τυπώνει πόσες εγγραφές δημιουργήθηκαν / υπήρχαν
ήδη για κάθε κατηγορία δεδομένων.

---

## 3. Custom Management Command: `import_club4paws`

**Αρχείο:** `products/management/commands/import_club4paws.py`

**Σκοπός:** Διαβάζει το αρχείο Word `OLA TA KEIMENA.docx` (κατάλογος προϊόντων CLUB4PAWS),
εξάγει δομημένα δεδομένα (όνομα, ζώο, κατηγορία, περιγραφή, components, variants με
βάρος/τιμή/SKU) και τα εισάγει στη βάση ως `Product` + `ProductVariant` εγγραφές.

**Προϋπόθεση:** Πρέπει να έχει ήδη τρέξει το `seed_data` (χρειάζεται να υπάρχει η εταιρεία
`CLUB4PAWS` στη βάση).

### Παράμετροι

| Παράμετρος | Υποχρεωτικό | Περιγραφή |
|---|---|---|
| `--file` | ✅ Ναι | Πλήρες path προς το αρχείο `.docx` |
| `--dry-run` | ❌ Όχι | Αν υπάρχει, κάνει μόνο parsing + preview, **χωρίς** να γράψει τίποτα στη βάση |

### Εκτέλεση — Δοκιμαστικό τρέξιμο (συνιστάται πρώτα)

```bash
python manage.py import_club4paws --file "/path/to/OLA TA KEIMENA.docx" --dry-run
```

Αυτό θα σου δείξει πόσα προϊόντα/variants θα δημιουργηθούν, ποια θα παραλειφθούν (π.χ.
multipacks), και ποια SKU είναι διπλότυπα — **χωρίς καμία αλλαγή στη βάση**. Ιδανικό για
έλεγχο πριν το πραγματικό import.

### Εκτέλεση — Πραγματικό import

```bash
python manage.py import_club4paws --file "/path/to/OLA TA KEIMENA.docx"
```

Είναι επίσης **idempotent**: αν το ξανατρέξεις με το ίδιο αρχείο, χρησιμοποιεί
`get_or_create()` πάνω στο `slug`/`sku`, οπότε δεν δημιουργεί διπλότυπα προϊόντα —
είτε ενημερώνει τα υπάρχοντα είτε τα προσπερνάει.

### Τι τυπώνει στο τέλος

- Πλήθος προϊόντων που δημιουργήθηκαν / ενημερώθηκαν.
- Πλήθος variants (μεγεθών/SKU) που δημιουργήθηκαν.
- Πλήθος blocks που παραλείφθηκαν επειδή δεν είχαν αναγνωρίσιμα δεδομένα.
- Προειδοποιήσεις για διπλότυπα SKU που αντικαταστάθηκαν με κενό.

> **Ενημέρωση:** Τα multipack/variety pack προϊόντα **δεν παραλείπονται πλέον** — αναγνωρίζονται
> αυτόματα και εισάγονται με `category = "Bundle"`. Στο dry-run output θα τα δεις με ετικέτα
> `[BUNDLE]` στο τέλος της γραμμής. Δες την ενότητα 9 του `README.md` για αναλυτική εξήγηση.
>
> **Ενημέρωση (τόνοι):** Κατά το import, τα ονόματα περνούν από `fix_greek_accents()`. Για ήδη
> εισαγμένα προϊόντα, τρέξε `fix_product_names` (ενότητα 3.1).

---

## 3.1 Custom Management Command: `fix_product_names`

**Αρχείο:** `products/management/commands/fix_product_names.py`

**Σκοπός:** Διορθώνει ελληνικούς τόνους στα `Product.name` που ήδη υπάρχουν στη βάση (π.χ. από
παλιό import). Χρησιμοποιεί την ίδια `fix_greek_accents()` με το `import_club4paws`.

**Είναι idempotent** — ασφαλές να ξανατρέξει.

### Παράμετροι

| Παράμετρος | Υποχρεωτικό | Περιγραφή |
|---|---|---|
| `--dry-run` | ❌ Όχι | Εμφανίζει τις αλλαγές χωρίς αποθήκευση |

### Εκτέλεση

```bash
python manage.py fix_product_names --dry-run
python manage.py fix_product_names
```

---

## 3.2 Custom Management Command: `set_initial_stock`

**Αρχείο:** `products/management/commands/set_initial_stock.py`

**Σκοπός:** Ορίζει το ίδιο `stock` σε **όλα** τα `ProductVariant` (default: **20**). Χρήσιμο
μετά από import (όπου αρχικά μπορεί να είναι 0) ή για μαζική ενημέρωση development.

> ⚠️ Σε production χρησιμοποίησε πραγματικούς αριθμούς ανά SKU — όχι μαζικό 20.

### Παράμετροι

| Παράμετρος | Υποχρεωτικό | Περιγραφή |
|---|---|---|
| `--stock` | ❌ Όχι | Ποσότητα για όλα τα variants (default: 20) |

### Εκτέλεση

```bash
python manage.py set_initial_stock
python manage.py set_initial_stock --stock 50
```

---

## 4. Custom Management Command: `link_photos`

**Αρχείο:** `products/management/commands/link_photos.py`

**Σκοπός:** Συνδέει αρχεία φωτογραφιών με τα αντίστοιχα `Product` records, ταιριάζοντας το
όνομα κάθε αρχείου (ή το SKU, για bundles) με τα ήδη υπάρχοντα προϊόντα στη βάση.

**Προϋπόθεση:** Τα προϊόντα πρέπει να έχουν ήδη εισαχθεί (π.χ. μέσω `import_club4paws`).

### Παράμετροι

| Παράμετρος | Υποχρεωτικό | Περιγραφή |
|---|---|---|
| `--base-dir` | ✅ Ναι | Φάκελος που περιέχει υποφακέλους ανά ζώο (πρέπει να έχουν "dog" ή "cat" στο όνομά τους, π.χ. "DOGS PHOTO", "CATS PHOTO") |
| `--dry-run` | ❌ Όχι | Δείχνει τι θα γίνει, **χωρίς** να αντιγράψει αρχεία ή να αλλάξει τη βάση |

### Εκτέλεση — Δοκιμαστικό τρέξιμο (συνιστάται πρώτα)

```bash
python manage.py link_photos --base-dir "/path/to/folder/with/DOGS PHOTO/and/CATS PHOTO" --dry-run
```

### Εκτέλεση — Πραγματική σύνδεση

```bash
python manage.py link_photos --base-dir "/path/to/folder/with/DOGS PHOTO/and/CATS PHOTO"
```

Είναι **idempotent** και **ασφαλές να ξανατρέξει**: ποτέ δεν αντικαθιστά μια φωτογραφία που
έχει ήδη ανατεθεί σε προϊόν μέσα στο ίδιο ή προηγούμενο τρέξιμο — αν δύο αρχεία ταιριάζουν στο
ίδιο προϊόν, κρατάει το πρώτο και αναφέρει το δεύτερο σαν πιθανό διπλότυπο.

### Τι τυπώνει στο τέλος

- Λίστα με κάθε φωτογραφία που συνδέθηκε, μαζί με τον τύπο match (`SKU match`, `name match`,
  `fuzzy match`, ή `best-effort guess`) ώστε να ξέρεις πόσο σίγουρο ήταν το ταίριασμα.
- Λίστα φωτογραφιών που παραλείφθηκαν επειδή το προϊόν-στόχος είχε ήδη φωτογραφία.
- Λίστα φωτογραφιών που δεν βρήκαν κανένα ταιριαστό προϊόν.
- Πλήθος προϊόντων που παραμένουν χωρίς φωτογραφία.

---

## 4.1 Custom Management Command: `import_company_logos`

**Αρχείο:** `products/management/commands/import_company_logos.py`

**Σκοπός:** Εισάγει τα brand logos από τον φάκελο assets του πελάτη
(`c:\Users\steli\KOKORIS_eshop\LOGOS` — WSL: `/mnt/c/Users/steli/KOKORIS_eshop/LOGOS`) στο
υπάρχον πεδίο `Company.logo` (ImageField). Χρησιμοποιείται για το homepage brand carousel.

**Προϋπόθεση:** Πρέπει να έχει ήδη τρέξει το `seed_data` (οι 7 εταιρείες πρέπει να υπάρχουν στη βάση).

### Mapping (Company → αρχείο)

| Company | Αρχείο LOGOS |
|---|---|
| CLUB4PAWS | `LOGO_CLUB4PAWS_FOTO.png` |
| Core | `LOGO_CORIS_PHOTO.pdf` → rasterized σε PNG |
| OWNAT | `LOGO_OWNAT_FOTO.png` |
| PROFINE | `LOGO_PROFINE_FOTO.png` |
| EVERCLEAN | `logo_Everclean_blue.jpg` |
| Wild Side | `LOGO_WILDSIDE_FOTO.png` |
| Puro Instinto | `pienso-puro-instinto.jpg` |

### Παράμετροι

| Παράμετρος | Υποχρεωτικό | Περιγραφή |
|---|---|---|
| `--force` | ❌ Όχι | Αντικαθιστά logos ακόμα κι αν υπάρχουν ήδη |
| `--logos-dir` | ❌ Όχι | Override path προς φάκελο LOGOS (default: WSL path παραπάνω) |

### Εκτέλεση

```bash
python manage.py seed_data
python manage.py import_company_logos
```

Για ανανέωση όλων των logos:

```bash
python manage.py import_company_logos --force
```

> **Σημείωση:** Το Core logo είναι PDF — χρειάζεται ImageMagick (`convert`) εγκατεστημένο στο
> σύστημα. Carnis δεν έχει ακόμα αρχείο στον φάκελο LOGOS.

### Έλεγχος αποτελέσματος

```bash
python manage.py shell -c "
from products.models import Company
for c in Company.objects.exclude(logo='').order_by('name'):
    print(c.name, '→', c.logo.name)
print('Total with logo:', Company.objects.exclude(logo='').count())
"
```

---

## 5. Part 2 — Authentication & Orders (νέα URLs, όχι management commands)

Το Part 2 δεν πρόσθεσε νέα management commands, αλλά νέα **apps** (`accounts`, `orders`) και νέες
**σελίδες/URLs**. Δες [`README.md`](README.md) ενότητα 11 για την πλήρη εξήγηση σχεδιασμού.

### Νέα URLs (δοκίμασέ τα μέσα από browser μόλις τρέχει ο server)

| URL | Περιγραφή |
|---|---|
| `/accounts/signup/` | Εγγραφή νέου πελάτη (email + password) |
| `/accounts/login/` | Σύνδεση (email + password, ή Google από auth modal — δες παρακάτω) |
| `/accounts/logout/` | Αποσύνδεση |
| `/accounts/password/reset/` | Ανάκτηση κωδικού μέσω email |
| `/accounts/profile/` | Στοιχεία παράδοσης πελάτη (τηλέφωνο, πόλη, διεύθυνση, Τ.Κ., οδηγίες) |

**Auth modal (UI):** το person icon στο nav ανοίγει modal (`templates/partials/auth-modal.html`) —
δεν χρειάζεται να πας στο `/accounts/login/` για καθημερινή χρήση. Οι ίδιες ροές allauth
παραμένουν διαθέσιμες ως URLs.

### Ενεργοποίηση πραγματικής σύνδεσης Google

Τα OAuth secrets φορτώνονται από το **`.env`** (όχι hardcoded στο `settings.py`):

```bash
cp .env.example .env
# Συμπλήρωσε:
# GOOGLE_OAUTH_CLIENT_ID=
# GOOGLE_OAUTH_CLIENT_SECRET=
```

Για Google: [Google Cloud Console](https://console.cloud.google.com) → OAuth 2.0 Client ID
(Authorized redirect URIs — **και τα δύο**):

- `http://localhost:8000/accounts/google/login/callback/`
- `http://127.0.0.1:8000/accounts/google/login/callback/`

Μετά:

```bash
python manage.py setup_oauth    # γράφει/ενημερώνει SocialApp στη βάση από .env
python manage.py check_oauth    # εμφανίζει redirect URI + διάγνωση credentials
```

Επανεκκίνησε τον server. Δοκίμασε «Σύνδεση με Google» από το auth modal.

**Σημείωση:** Αν βλέπεις `redirect_uri_mismatch`, σύγκρινε την έξοδο του `check_oauth` με τα
URIs στο Google Console (ίδιο GCP project, Testing mode + test users αν χρειάζεται).

Για Facebook: [Facebook Developers](https://developers.facebook.com) — δες README ενότητα 11.2
(αν ενεργοποιηθεί provider αργότερα).

### Πώς φτιάχνεις μια δοκιμαστική παραγγελία μέσα από το shell (για tests)

> **Ενημέρωση (Part 4):** από εδώ και πέρα, οι πραγματικές παραγγελίες δημιουργούνται πάντα μέσω
> της ροής checkout (`/checkout/address/` → `/checkout/delivery/` → `/checkout/payment/`, δες
> ενότητα 5.3 παρακάτω), όχι χειροκίνητα μέσω shell — το `Order` έχει πλέον υποχρεωτικά πεδία
> (`cart_cost`, `total_cost`, `delivery_method`, στοιχεία παράδοσης) που η ροή checkout
> συμπληρώνει αυτόματα. Το παρακάτω παραμένει μόνο ως ιστορική αναφορά για το πώς ήταν το
> μοντέλο στο Part 2 (πριν το `total_amount` μετονομαστεί σε `cart_cost`).

```bash
python manage.py shell -c "
from accounts.models import CustomUser
from orders.models import Order, OrderItem
from products.models import ProductVariant

user = CustomUser.objects.first()
variant = ProductVariant.objects.first()
order = Order.objects.create(
    user=user, payment_method=Order.PAYMENT_METHOD_COD,
    cart_cost=variant.price * 2, total_cost=variant.price * 2,
    delivery_method=Order.DELIVERY_METHOD_COMPANY,
    delivery_phone_number='6900000000', delivery_city='Athens', delivery_address='Test 1',
    delivery_postal_code='11525', delivery_latitude=37.9838, delivery_longitude=23.7275,
)
OrderItem.objects.create(order=order, product_variant=variant, quantity=2, price_at_purchase=variant.price)
print(order, list(order.items.all()))
"
```

### Πώς έγινε το reset της βάσης για το custom User model (αναφορά, όχι κάτι να ξανατρέξεις)

Επειδή το `AUTH_USER_MODEL` πρέπει να οριστεί πριν το πρώτο `migrate`, χρειάστηκε ένα **one-time**
reset της τοπικής βάσης όταν προστέθηκε το `accounts.CustomUser`. Κρατάμε εδώ τα βήματα σαν
αναφορά, σε περίπτωση που χρειαστεί ποτέ κάτι ανάλογο ξανά (π.χ. σε νέο μηχάνημα πριν υπάρχουν
πραγματικοί πελάτες):

```bash
# 1. Backup πρώτα (ποτέ μην κάνεις reset χωρίς backup)
python manage.py dumpdata products --indent 2 > backups/products_backup_$(date +%Y%m%d).json
cp db.sqlite3 backups/db_before_reset.sqlite3

# 2. Reset
rm db.sqlite3
python manage.py makemigrations
python manage.py migrate

# 3. Ξαναγέμισμα με τα ήδη υπάρχοντα scripts
python manage.py seed_data
python manage.py import_club4paws --file "/path/to/OLA TA KEIMENA.docx"
python manage.py link_photos --base-dir "/path/to/folder/with/DOGS PHOTO/and/CATS PHOTO"
python manage.py fix_product_names
python manage.py set_initial_stock
python manage.py createsuperuser
```

---

## 5.1 Νέο πεδίο `availability` στο `ProductVariant`

Δεν είναι management command, αλλά ένα νέο πεδίο (`products/models.py`) με 3 χειροκίνητες τιμές:
`available_now`, `on_order`, `out_of_stock` (δες README ενότητα 11.8 για την πλήρη εξήγηση).
Ενημερώνεται από το ίδιο σημείο με το `stock`, στο Admin: **Products → Product Variants**, με
inline επεξεργασία στη λίστα (`list_editable`) — δεν χρειάζεται να ανοίξεις κάθε εγγραφή ξεχωριστά.

---

## 5.2 Part 3 — Cart App (νέα εφαρμογή, όχι management command)

Το Part 3 δεν πρόσθεσε management command, αλλά μια νέα εφαρμογή **`cart`** με δύο "backends"
πίσω από κοινό interface — δες [`README.md`](README.md) ενότητα 12 για την πλήρη εξήγηση
σχεδιασμού. Παρακάτω είναι έτοιμα inline scripts (`manage.py shell -c "..."`) για να δοκιμάσεις
τη λειτουργία χειροκίνητα.

> ⚠️ Όλα τα παρακάτω δημιουργούν *δοκιμαστικά* δεδομένα (test user, προσωρινές τιμές `stock`).
> Αν τα τρέξεις σε production/πραγματική βάση, θυμήσου να τα καθαρίσεις μετά (δες το τελευταίο
> script παρακάτω, "Καθαρισμός δοκιμαστικών δεδομένων").

### Καλάθι συνδεδεμένου χρήστη (`DBCart`)

```bash
python manage.py shell -c "
from accounts.models import CustomUser
from products.models import ProductVariant
from cart.cart import DBCart, CartError

# Δημιουργεί έναν ΚΑΘΑΡΑ δοκιμαστικό χρήστη — δεν αγγίζει ποτέ υπαρκτό/πραγματικό λογαριασμό
# (π.χ. ποτέ CustomUser.objects.first(), που θα μπορούσε να είναι ο πραγματικός admin).
user, _ = CustomUser.objects.get_or_create(email='cart_test@example.com')
variant = ProductVariant.objects.first()
variant.stock = 5
variant.save(update_fields=['stock'])

cart = DBCart(user)
cart.add_item(variant, quantity=2)
print('Σύνολο τεμαχίων:', cart.total_items, '| Σύνολο αξίας:', cart.total)

cart.update_item(variant, new_quantity=4)
print('Μετά την ενημέρωση ποσότητας:', cart.items[0].quantity)

try:
    cart.add_item(variant, quantity=10)  # ξεπερνά το stock=5
except CartError as e:
    print('Αναμενόμενο σφάλμα stock:', e)
"
```

### Καλάθι επισκέπτη (`SessionCart`) — μέσω Django test Client

Επειδή το guest καλάθι ζει μέσα στο session, χρειάζεται ένα πραγματικό αντικείμενο session
(όχι απλό dict) για να το δοκιμάσουμε ρεαλιστικά — το `django.test.Client` το παρέχει έτοιμο:

```bash
python manage.py shell -c "
from django.test import Client
from products.models import ProductVariant

variant = ProductVariant.objects.first()
variant.stock = 5
variant.save(update_fields=['stock'])

client = Client()
session = client.session
session['cart'] = {}
session.save()

from cart.cart import SessionCart
guest_cart = SessionCart(session)
guest_cart.add_item(variant, quantity=2)
session.save()
print('Guest cart μετά την προσθήκη:', session.get('cart'))
"
```

### Merge guest → user καλαθιού κατά το login

```bash
python manage.py shell -c "
from django.test import Client
from accounts.models import CustomUser
from products.models import ProductVariant
from cart.models import Cart

# Δημιουργεί έναν ΚΑΘΑΡΑ δοκιμαστικό χρήστη — δεν αγγίζει ποτέ υπαρκτό/πραγματικό λογαριασμό.
user, _ = CustomUser.objects.get_or_create(email='cart_test@example.com')
user.set_password('temporary-test-pass')
user.save()

variant = ProductVariant.objects.first()
variant.stock = 5
variant.save(update_fields=['stock'])

client = Client()
session = client.session
session['cart'] = {str(variant.pk): 2}
session.save()
print('Πριν το login, session key:', session.session_key, '| cart:', session.get('cart'))

client.login(email=user.email, password='temporary-test-pass')

new_session = client.session
print('Μετά το login, session key (αλλάζει):', new_session.session_key)
print('Guest cart μετά το login (πρέπει να είναι άδειο):', new_session.get('cart'))
print('DB cart του χρήστη:', list(Cart.objects.get(user=user).items.values('product_variant_id', 'quantity')))
"
```

### Καθαρισμός δοκιμαστικών δεδομένων

Μετά από οποιοδήποτε από τα παραπάνω scripts, τρέξε αυτό για να επαναφέρεις τη βάση καθαρή:

```bash
python manage.py shell -c "
from products.models import ProductVariant
from accounts.models import CustomUser

ProductVariant.objects.filter(stock__gt=0).update(stock=0)
CustomUser.objects.filter(email='cart_test@example.com').delete()  # διαγράφει και το Cart του (CASCADE)
"
```

> ⚠️ Αν κάποιο από τα παραπάνω scripts εκτελεστεί με λάθος τροποποιημένη εντολή (π.χ.
> `CustomUser.objects.first()` αντί για τον αποκλειστικά δοκιμαστικό λογαριασμό
> `cart_test@example.com`), μπορεί να δημιουργηθεί κατά λάθος καλάθι στον **πραγματικό**
> λογαριασμό admin. Έλεγξε με `python manage.py shell -c "from cart.models import Cart;
> print(list(Cart.objects.all()))"` και διάγραψε ό,τι δεν είναι δικό σου δοκιμαστικό δεδομένο.
>
> **Σημείωση stock:** Το default `stock` για νέα variants είναι **20**. Το script καθαρισμού
> παρακάτω μηδενίζει stock μόνο για δοκιμές — **μην** το τρέξεις σε production DB.

---

## 5.3 Part 4 — Checkout App (νέα εφαρμογή, όχι management command)

Το Part 4 δεν πρόσθεσε management command, αλλά μια νέα εφαρμογή **`checkout`** (ροή 3 βημάτων:
διεύθυνση → τρόπος παράδοσης → πληρωμή) — δες [`README.md`](README.md) ενότητα 15 για την πλήρη
εξήγηση σχεδιασμού.

### Νέα URLs (δοκίμασέ τα μέσα από browser, μόλις τρέχει ο server, αφού πρώτα βάλεις κάτι στο
### καλάθι σου και κάνεις login)

| URL | Περιγραφή |
|---|---|
| `/checkout/address/` | Βήμα 1: διεύθυνση παράδοσης (χρειάζεται πραγματικό, ενεργό `GOOGLE_MAPS_API_KEY` με billing) |
| `/checkout/delivery/` | Βήμα 2: επιλογή τρόπου παράδοσης |
| `/checkout/payment/` | Βήμα 3: επιλογή πληρωμής + δημιουργία παραγγελίας |
| `/checkout/confirmation/<id>/` | Επιβεβαίωση παραγγελίας + κουμπί ακύρωσης |
| `/orders/<id>/cancel/` | POST-only, ακύρωση παραγγελίας από τον ιδιοκτήτη της |

### Δοκιμή πλήρους ροής checkout μέσω script (ό,τι τρέξαμε κι εμείς για επαλήθευση)

Χρειάζεται ένα **τρέχον `runserver`** (πραγματικά HTTP requests, όχι Django test `Client`), και
τη βιβλιοθήκη `requests` (ήδη στο `requirements.txt`). Δημιουργεί δοκιμαστικό χρήστη/παραγγελίες
και τα καθαρίζει μόνο του στο τέλος — **δεν** αγγίζει ποτέ πραγματικά δεδομένα, εκτός από το να
ανεβάσει προσωρινά το `stock` ενός τυχαίου variant (το επαναφέρει στο τέλος).

```bash
# Τερματικό 1
python manage.py runserver

# Τερματικό 2 — αποθήκευσε το παρακάτω σαν test_checkout_flow.py και τρέξε python test_checkout_flow.py
```

```python
import os, re
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import requests
from accounts.models import CustomUser
from cart.models import Cart, CartItem
from orders.models import Order
from products.models import ProductVariant

BASE = "http://127.0.0.1:8000"
EMAIL, PASSWORD = "checkout_test@example.com", "checkouttestpass123"

def csrf_from(html):
    return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)

user, _ = CustomUser.objects.get_or_create(email=EMAIL)
user.set_password(PASSWORD); user.save()
Cart.objects.filter(user=user).delete()
cart = Cart.objects.create(user=user)
variant = ProductVariant.objects.filter(availability="available_now").first()
original_stock = variant.stock
variant.stock = 10; variant.save(update_fields=["stock"])
CartItem.objects.create(cart=cart, product_variant=variant, quantity=2)

s = requests.Session()
r = s.get(f"{BASE}/accounts/login/")
s.post(f"{BASE}/accounts/login/", data={"csrfmiddlewaretoken": csrf_from(r.text), "login": EMAIL, "password": PASSWORD})

r = s.get(f"{BASE}/checkout/address/")
r = s.post(f"{BASE}/checkout/address/", data={
    "csrfmiddlewaretoken": csrf_from(r.text), "phone_number": "6912345678", "city": "Athens",
    "address": "Ermou 1", "postal_code": "11525", "floor": "2", "latitude": "37.9838",
    "longitude": "23.7275", "delivery_notes": "", "preferred_delivery_time": "",
}, allow_redirects=False)

r = s.get(f"{BASE}/checkout/delivery/")
r = s.post(f"{BASE}/checkout/delivery/", data={
    "csrfmiddlewaretoken": csrf_from(r.text), "delivery_method": "company_delivery",
}, allow_redirects=False)

r = s.get(f"{BASE}/checkout/payment/")
r = s.post(f"{BASE}/checkout/payment/", data={
    "csrfmiddlewaretoken": csrf_from(r.text), "payment_method": "cash_on_delivery",
}, allow_redirects=False)
order_id = int(r.headers["Location"].rstrip("/").rsplit("/", 1)[-1])
print("Order created:", Order.objects.get(id=order_id))

# Καθαρισμός
Order.objects.filter(user=user).delete()
Cart.objects.filter(user=user).delete()
user.delete()
variant.stock = original_stock; variant.save(update_fields=["stock"])
```

> ⚠️ Αν τρέξεις κάτι παρόμοιο ξανά αργότερα, θυμήσου να **σβήσεις** το προσωρινό script αρχείο
> μετά (δεν είναι μόνιμο μέρος του project, ούτε test suite).

---

## 5.4 Part 5 — Catalog, Cart API & Wishlist (νέα URLs/JS)

Το Part 5 πρόσθεσε catalog grid, JSON cart endpoints και wishlist toggle — δες [`README.md`](README.md)
ενότητες 16.6, 12.8 και 18.

### Catalog URLs (browser)

| URL | Περιγραφή |
|---|---|
| `/products/all/` | Όλα τα προϊόντα (προαιρετικό `?brand=CLUB4PAWS`) |
| `/products/dogs/` | Προϊόντα σκύλου |
| `/products/cats/` | Προϊόντα γάτας |
| `/products/brands/` | Grid μαρκών → link με φίλτρο brand |

### Cart HTTP API (JSON — χρησιμοποιείται από `static/js/catalog.js`)

| URL | Μέθοδος | Body | Απάντηση |
|---|---|---|---|
| `/cart/add/` | POST | `variant_id` (+ CSRF) | `{ ok, total_items, quantities, variant_id, quantity }` |
| `/cart/update/` | POST | `variant_id`, `quantity` (0 = αφαίρεση) | ίδιο format |
| `/cart/status/` | GET | — | `{ ok, total_items, quantities }` |

Δέχεται `application/json` ή form POST. Σφάλματα stock: `{ ok: false, error: "..." }` HTTP 400.

### Wishlist (σελίδα + API)

| URL | Μέθοδος | Auth | Τι κάνει |
|---|---|---|---|
| `/wishlist/` | GET | Όλοι | Σελίδα αγαπημένων |
| `/wishlist/toggle/` | POST | Όλοι | Toggle `product_id` — guest session ή DB |
| `/wishlist/status/` | GET | Όλοι | `{ ok, product_ids, total_items }` |

Απάντηση toggle: `{ ok, wishlisted, total_items }`. Merge guest → user στο login (`wishlist/signals.py`).

### Δοκιμή cart status από terminal (με cookies/session)

```bash
python manage.py runserver
# Σε άλλο terminal — χρειάζεται session cookie από browser ή Django test client
curl -s http://127.0.0.1:8000/cart/status/
```

Για πλήρη δοκιμή add/update, άνοιξε `/products/all/` στο browser και πάτα «Αγορά» σε προϊόν.

### Management commands (μετά import)

```bash
python manage.py fix_product_names      # τόνοι σε ονόματα προϊόντων
python manage.py set_initial_stock      # stock=20 σε όλα τα variants
```

---

## 7. Newsletter app (όχι management command)

Το `newsletter` app δεν έχει management command — η εγγραφή γίνεται από τη φόρμα στο footer
της αρχικής σελίδας. Δες [`README.md`](README.md) ενότητα 17 για πλήρη εξήγηση.

### Έλεγχοι email (επιβεβαιωμένο)

- **Μορφή:** browser `type="email" required` + Django `EmailField` στο form + `EmailField` στο model.
- **Διπλότυπα:** `email` με `unique=True` στη βάση + `get_or_create()` με lowercase normalization.
  Δεύτερη ενεργή εγγραφή με το ίδιο email **δεν** δημιουργεί νέα εγγραφή — εμφανίζεται μήνυμα
  «ήδη εγγεγραμμένο».

### reCAPTCHA v3

Η φόρμα προστατεύεται με Google reCAPTCHA v3. Τα keys μπαίνουν στο `.env` (gitignored).
Για OAuth και Maps, δες επίσης `.env.example`:

```bash
cp .env.example .env
# RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY
# GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET
# GOOGLE_MAPS_API_KEY
```

Έλεγχος ότι φορτώνονται:

```bash
python manage.py shell -c "
from django.conf import settings
print('RECAPTCHA_ENABLED:', settings.RECAPTCHA_ENABLED)
"
```

Αν `RECAPTCHA_ENABLED: True`, στο footer εμφανίζεται το μήνυμα reCAPTCHA και η φόρμα
στέλνει token πριν το submit. Keys από [Google reCAPTCHA Admin](https://www.google.com/recaptcha/admin)
(τύπος v3, domains: `localhost` + production domain).

### URL

| URL | Μέθοδος | Περιγραφή |
|---|---|---|
| `/newsletter/subscribe/` | POST | Αποθήκευση email από footer (CSRF-protected) |

### Διαχείριση από Admin

`http://localhost:8000/admin/newsletter/newslettersubscriber/`

- **Export selected emails as CSV** — για bulk email tools.
- **Mark selected as unsubscribed** — απενεργοποίηση χωρίς διαγραφή.

### Έλεγχος λίστας από shell

```bash
python manage.py shell -c "
from newsletter.models import NewsletterSubscriber
for s in NewsletterSubscriber.objects.all():
    print(s.email, s.is_active, s.subscribed_at)
print('Σύνολο:', NewsletterSubscriber.objects.count())
"
```

### Δοκιμή εγγραφής (χειροκίνητα)

1. Τρέξε `python manage.py runserver`.
2. Άνοιξε `http://localhost:8000/` και κύλισε στο footer.
3. Βάλε email → «Εγγραφή» → θα εμφανιστεί μήνυμα επιτυχίας/ήδη εγγεγραμμένου πάνω από τη σελίδα.
4. Επανάλαβε με το **ίδιο** email — πρέπει να δεις «ήδη εγγεγραμμένο», όχι δεύτερη εγγραφή στο admin.
5. Δοκίμασε `not-an-email` — πρέπει να απορριφθεί (browser ή server validation).

---

## 8. Wishlist app (όχι management command)

Το `wishlist` app δεν έχει management command — η προσθήκη/αφαίρεση γίνεται από το catalog grid
(heart icon). Δες [`README.md`](README.md) ενότητα 18.

### URL

| URL | Μέθοδος | Auth | Περιγραφή |
|---|---|---|---|
| `/wishlist/toggle/` | POST | Login required | Toggle προϊόν (`product_id`) · JSON |

### Admin

`http://localhost:8000/admin/wishlist/wishlistitem/`

### Έλεγχος από shell

```bash
python manage.py shell -c "
from wishlist.models import WishlistItem
for w in WishlistItem.objects.select_related('user','product')[:10]:
    print(w.user.email, '->', w.product.name)
print('Σύνολο:', WishlistItem.objects.count())
"
```

---

## 9. Βοηθητικά scripts επαλήθευσης (μη-management commands)

Αυτά δεν είναι μόνιμα αρχεία στο repo, αλλά inline εντολές μέσω `manage.py shell -c "..."`
που χρησιμοποιήσαμε για επαλήθευση μετά το import. Τις κρατάμε εδώ ως αναφορά, σε περίπτωση
που χρειαστεί να ξανατρέξεις παρόμοιους ελέγχους:

### Συνολικά στατιστικά

```bash
python manage.py shell -c "
from products.models import Company, AnimalType, Category, Product, ProductVariant
print('Companies:', Company.objects.count())
print('Animal Types:', AnimalType.objects.count())
print('Categories:', Category.objects.count())
print('Products:', Product.objects.count())
print('Variants:', ProductVariant.objects.count())
"
```

### Έλεγχος για διπλότυπα SKU

```bash
python manage.py shell -c "
from django.db.models import Count
from products.models import ProductVariant
dupes = (ProductVariant.objects.exclude(sku__isnull=True).exclude(sku='')
         .values('sku').annotate(n=Count('id')).filter(n__gt=1))
print(list(dupes))
"
```

### Καταμέτρηση προϊόντων ανά κατηγορία/ζώο

```bash
python manage.py shell -c "
from products.models import Product
for c in Product.objects.values_list('category__name', flat=True).distinct():
    print(c, Product.objects.filter(category__name=c).count())
"
```

---

## 10. Ροή εργασίας από το μηδέν (setup σε νέο μηχάνημα)

Αν χρειαστεί να στήσεις το project σε άλλο μηχάνημα (ή μετά από `git clone`):

```bash
git clone git@github.com:spatroudakis/kokkoris_eshop.git
# ή HTTPS αν δεν έχεις SSH: git clone https://github.com/spatroudakis/kokkoris_eshop.git
cd kokkoris_eshop
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # RECAPTCHA, Google OAuth, Maps keys
python manage.py migrate
DJANGO_SUPERUSER_EMAIL=admin@kokkoriseshop.local DJANGO_SUPERUSER_PASSWORD=admin12345 \
  python manage.py createsuperuser --noinput
python manage.py setup_oauth   # αν έχεις GOOGLE_OAUTH_* στο .env
python manage.py seed_data
python manage.py import_club4paws --file "/path/to/OLA TA KEIMENA.docx"
python manage.py link_photos --base-dir "/path/to/folder/with/DOGS PHOTO/and/CATS PHOTO"
python manage.py import_company_logos    # brand logos (αν υπάρχει φάκελος LOGOS)
python manage.py fix_product_names     # διόρθωση τόνων (προαιρετικό μετά import)
python manage.py set_initial_stock     # stock=20 σε όλα τα variants
python manage.py runserver
```

> **Δεν** έρχονται από Git: `db.sqlite3`, `media/`, `.env` — πρέπει να τρέξεις imports και
> να αντιγράψεις/δημιουργήσεις `.env` τοπικά.
>
> Σημείωση: `createsuperuser` ζητάει πλέον **email** αντί για username (δες ενότητα 1).
