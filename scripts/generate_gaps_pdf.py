#!/usr/bin/env python3
"""Company-by-company gaps PDF — saved to Windows Downloads."""
from collections import Counter
from pathlib import Path

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from fpdf import FPDF
from products.company_pages import has_brand_page
from products.models import Company, Product, ProductVariant

OUTPUT = Path("/mnt/c/Users/steli/Downloads/Kokkoris_Eshop_Ti_Leipei.pdf")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

TEAL = (30, 80, 72)
ORANGE = (180, 90, 20)
RED = (150, 40, 40)
OK = (30, 110, 70)
MUTED = (90, 90, 90)
INK = (30, 30, 30)
LINE = (210, 210, 210)
ROW_ALT = (245, 248, 247)
HEAD_BG = (30, 80, 72)


class PDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("DejaVu", size=8)
        self.set_text_color(130, 130, 130)
        self.cell(
            0,
            8,
            f"Kokkoris Pet Food — τι λείπει ανά εταιρεία    {self.page_no()}/{{nb}}",
            align="C",
        )


def mix_label(active_qs):
    mix = Counter()
    for product in active_qs.select_related("animal_type", "category"):
        animal = product.animal_type.name if product.animal_type else "?"
        category = product.category.name if product.category else "?"
        greek_animal = {"Dog": "σκύλος", "Cat": "γάτα"}.get(animal, animal)
        greek_cat = {
            "Dry Food": "ξηρά",
            "Sachets": "φακελάκια",
            "Canned Food": "κονσέρβες",
            "Litter": "άμμος",
            "Bundle": "πακέτα",
        }.get(category, category)
        mix[f"{greek_animal} / {greek_cat}"] += 1
    return ", ".join(f"{name} {count}" for name, count in sorted(mix.items()))


def build_pdf():
    companies = list(Company.objects.order_by("name"))
    rows = []
    for company in companies:
        products = Product.objects.filter(company=company)
        active = products.filter(is_active=True)
        inactive = products.filter(is_active=False)
        variants = ProductVariant.objects.filter(product__company=company)
        no_img = [p for p in active if not p.image]
        zero_price = list(variants.filter(price=0))
        empty_sku = list(variants.filter(sku__isnull=True)) + list(
            variants.filter(sku="")
        )
        # de-dupe empty sku by id
        seen = set()
        empty_unique = []
        for variant in empty_sku:
            if variant.id not in seen:
                seen.add(variant.id)
                empty_unique.append(variant)

        if not has_brand_page(company.code) and active.count():
            verdict = "Λείπει σελίδα brand"
            tone = "warn"
        elif active.count() == 0 and inactive.count() == 0:
            verdict = "Λείπουν όλα τα προϊόντα"
            tone = "bad"
        elif active.count() == 0 and inactive.count():
            verdict = "Drafts χωρίς τιμές"
            tone = "bad"
        elif no_img:
            verdict = f"Λείπουν {len(no_img)} φωτο"
            tone = "warn"
        else:
            verdict = "Κατάλογος εντάξει"
            tone = "ok"

        rows.append(
            {
                "name": company.name,
                "code": company.code,
                "page": has_brand_page(company.code),
                "active": active.count(),
                "inactive": inactive.count(),
                "variants": variants.count(),
                "no_img": no_img,
                "zero_price": zero_price,
                "empty_sku": empty_unique,
                "inactive_list": list(inactive),
                "mix": mix_label(active) if active.exists() else "—",
                "verdict": verdict,
                "tone": tone,
            }
        )

    core_folder = Path(
        "/mnt/c/Users/steli/Downloads/transfer-01a04784/CORE_PHOTO & KEIMENA/PROIONTA"
    )
    core_files = {p.stem.upper() for p in core_folder.glob("*.png")}
    core_db = {
        (v.sku or "").upper(): v
        for v in ProductVariant.objects.filter(product__company__code="COR").select_related(
            "product"
        )
    }
    c4p_folder = Path(
        "/mnt/c/Users/steli/Downloads/transfer-01a04784/KEIMENA & PHOTO CLUB4PAWS/PHOTO"
    )
    c4p_files = {p.stem.upper() for p in c4p_folder.glob("*.png")}
    c4p_db = {
        (v.sku or "").upper(): v
        for v in ProductVariant.objects.filter(product__company__code="C4P").select_related(
            "product"
        )
    }

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(14, 16, 14)
    pdf.add_font("DejaVu", "", FONT)
    pdf.add_font("DejaVuB", "", FONT_BOLD)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    def ensure(space=28):
        if pdf.get_y() > 297 - 18 - space:
            pdf.add_page()

    def h1(text):
        pdf.set_font("DejaVuB", size=17)
        pdf.set_text_color(*TEAL)
        pdf.multi_cell(width, 8, text)

    def h2(text):
        ensure(24)
        pdf.ln(5)
        pdf.set_font("DejaVuB", size=12)
        pdf.set_text_color(*TEAL)
        pdf.multi_cell(width, 7, text)
        pdf.ln(1)

    def body(text, color=INK):
        pdf.set_font("DejaVu", size=10)
        pdf.set_text_color(*color)
        pdf.multi_cell(width, 5.4, text)
        pdf.ln(0.6)

    def bullet(text, color=INK):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("DejaVu", size=10)
        pdf.set_text_color(*color)
        pdf.multi_cell(width, 5.3, f"   •  {text}")
        pdf.set_x(pdf.l_margin)

    def kv(label, value):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("DejaVuB", size=10)
        pdf.set_text_color(*TEAL)
        pdf.cell(44, 5.6, label, ln=0)
        pdf.set_font("DejaVu", size=10)
        pdf.set_text_color(*INK)
        pdf.multi_cell(width - 44, 5.6, value)
        pdf.set_x(pdf.l_margin)

    h1("Τι λείπει ανά εταιρεία")
    pdf.set_font("DejaVu", size=10)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        width,
        5.5,
        "Αναφορά καταλόγου Kokkoris Pet Food — σελίδα brand, προϊόντα, τιμές, "
        "φωτογραφίες. 2 Σεπτεμβρίου 2026.",
    )
    pdf.ln(4)

    # --- summary table ---
    pdf.set_font("DejaVuB", size=12)
    pdf.set_text_color(*TEAL)
    pdf.multi_cell(width, 7, "Σύνοψη εταιρειών")
    pdf.ln(2)

    col_w = [36, 26, 30, 20, 22, width - 134]
    headers = ["Εταιρεία", "Σελίδα", "Προϊόντα", "Τιμές", "Φωτο", "Τι λείπει"]

    def draw_row(cells, bold=False, fill=None, colors=None):
        pdf.set_font("DejaVuB" if bold else "DejaVu", size=8)
        x0 = pdf.l_margin
        y0 = pdf.get_y()
        # measure height
        heights = []
        for i, cell in enumerate(cells):
            heights.append(pdf.get_string_width(cell) / (col_w[i] - 2) * 4.2 + 6)
        h = max(8.2, min(18, max(heights)))
        if y0 + h > 275:
            pdf.add_page()
            y0 = pdf.get_y()
            # reprint header
            _header_row()
            y0 = pdf.get_y()
        for i, cell in enumerate(cells):
            if fill:
                pdf.set_fill_color(*fill)
            pdf.set_xy(x0 + sum(col_w[:i]), y0)
            if colors and colors[i]:
                pdf.set_text_color(*colors[i])
            elif bold:
                pdf.set_text_color(255, 255, 255)
            else:
                pdf.set_text_color(*INK)
            pdf.multi_cell(
                col_w[i],
                h / max(1, 1 + cell.count("\n")),
                cell,
                border=0,
                fill=bool(fill),
                align="L",
            )
        pdf.set_xy(x0, y0)
        pdf.set_draw_color(*LINE)
        pdf.rect(x0, y0, sum(col_w), h)
        x = x0
        for w in col_w[:-1]:
            x += w
            pdf.line(x, y0, x, y0 + h)
        pdf.set_y(y0 + h)

    def _header_row():
        pdf.set_fill_color(*HEAD_BG)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("DejaVuB", size=8)
        x0 = pdf.l_margin
        y0 = pdf.get_y()
        h = 8
        pdf.rect(x0, y0, sum(col_w), h, "F")
        x = x0
        for i, head in enumerate(headers):
            pdf.set_xy(x, y0 + 1.6)
            pdf.cell(col_w[i], 5, head)
            x += col_w[i]
        pdf.set_y(y0 + h)

    _header_row()
    for i, row in enumerate(rows):
        if row["active"]:
            products_cell = f"{row['active']} ενεργά"
        elif row["inactive"]:
            products_cell = f"0 ενεργά\n({row['inactive']} drafts)"
        else:
            products_cell = "0"

        if row["active"] == 0 and row["inactive"] == 0:
            prices_cell = "—"
            photos_cell = "—"
        elif row["zero_price"] and not row["active"]:
            prices_cell = "0,00 €"
            photos_cell = "ναι (drafts)"
        elif row["no_img"]:
            prices_cell = "ναι"
            photos_cell = f"{row['active'] - len(row['no_img'])}/{row['active']}"
        else:
            prices_cell = "ναι"
            photos_cell = f"{row['active']}/{row['active']}"

        tone_color = {"ok": OK, "warn": ORANGE, "bad": RED}[row["tone"]]
        draw_row(
            [
                f"{row['name']}\n{row['code']}",
                "ναι" if row["page"] else "ΟΧΙ",
                products_cell,
                prices_cell,
                photos_cell,
                row["verdict"],
            ],
            fill=ROW_ALT if i % 2 else (255, 255, 255),
            colors=[INK, ORANGE if not row["page"] else OK, INK, INK, INK, tone_color],
        )

    # missing company
    draw_row(
        [
            "Gaherdog / Gahercat",
            "ΟΧΙ",
            "0",
            "—",
            "—",
            "Δεν υπάρχει στη βάση",
        ],
        fill=(255, 244, 236),
        colors=[INK, RED, INK, INK, INK, RED],
    )
    pdf.ln(3)
    body(
        "Παρακάτω, μία εταιρεία τη φορά: τι υπάρχει ήδη και τι πρέπει να σταλεί.",
        MUTED,
    )

    # --- per company ---
    detail = {row["code"]: row for row in rows}

    h2("1. CLUB4PAWS  (C4P)")
    row = detail["C4P"]
    kv("Σελίδα brand", "Ναι — /products/company/C4P/  (από sel_club4paws.pdf)")
    kv("Προϊόντα shop", f"{row['active']} ενεργά, {row['variants']} μεγέθη. {row['mix']}.")
    kv("Τιμές", "Όλες συμπληρωμένες (καμία 0,00 €).")
    kv("Φωτο shop", "Και τα 62 προϊόντα έχουν εικόνα.")
    body("Τι λείπει:")
    bullet(
        "4 SKU της βάσης δεν έχουν αντίστοιχο αρχείο στον φάκελο PHOTO "
        "(τα προϊόντα έχουν ήδη άλλη φωτο): 71C1002, 86C210Μ, 86C250Μ1, 86C901."
    )
    bullet(
        "Το προϊόν «Αρνί ξηρά τροφή Indoor 4 σε 1 - για γάτες» έχει 2 μεγέθη "
        "(2 kg / 14 kg, τιμές 13,50 € και 63,00 €) με ΚΕΝΟ SKU."
    )
    extra = sorted(c4p_files - {s for s in c4p_db if s})
    if extra:
        bullet(
            "Αρχεία στον φάκελο PHOTO χωρίς SKU στη βάση: " + ", ".join(extra) + "."
        )
    body("Να σταλεί: SKU για το Indoor 4 σε 1 αρνί, και φωτο/SKU για τα 4 παραπάνω αν υπάρχουν.")

    h2("2. Core  (COR)")
    row = detail["COR"]
    kv("Σελίδα brand", "Ναι — /products/company/COR/")
    kv("Προϊόντα shop", f"{row['active']} ενεργά, {row['variants']} μεγέθη. {row['mix']}.")
    kv("Τιμές", "Όλες συμπληρωμένες (καμία 0,00 €).")
    kv("Φωτο shop", f"{row['active'] - len(row['no_img'])} από {row['active']} έχουν εικόνα.")
    body(
        "Έλεγχος φακέλου CORE_PHOTO & KEIMENA / PROIONTA: 60 αρχεία. "
        "Όλα αντιστοιχούν σε SKU που υπάρχουν ήδη στο shop. "
        "Δεν λείπει προϊόν που να έχει φωτο στον φάκελο και να μην είναι στο κατάστημα."
    )
    body("Τι λείπει — 4 κονσέρβες Savoury Medleys χωρίς φωτογραφία (τιμή 2,10 € η μία):")
    for product in row["no_img"]:
        sku = ", ".join(s for s in product.variants.values_list("sku", flat=True) if s)
        bullet(f"{sku}  —  {product.name}")
    body(
        "Το SKU 7880112 (δεύτερο μέγεθος Kitten) δεν έχει δικό του αρχείο στον φάκελο· "
        "το προϊόν έχει ήδη φωτο από το 7880111. Δεν είναι κενό."
    )
    body("Να σταλεί: 4 φωτο Savoury Medleys (7876410, 7876420, 7876430, 7876440).")

    h2("3. OWNAT  (OWN)")
    row = detail["OWN"]
    kv("Σελίδα brand", "Ναι — /products/company/OWN/")
    kv("Προϊόντα shop", f"{row['active']} ενεργά, {row['variants']} μεγέθη. {row['mix']}.")
    kv("Τιμές", "Όλες συμπληρωμένες.")
    kv("Φωτο shop", "Και τα 32 προϊόντα έχουν εικόνα.")
    body("Τι λείπει: τίποτα στον κατάλογο. Η σελίδα και τα προϊόντα είναι εντάξει.")

    h2("4. PROFINE  (PRF)")
    row = detail["PRF"]
    kv("Σελίδα brand", "ΟΧΙ — το κλικ στη μάρκα ανοίγει τον κατάλογο φιλτραρισμένο.")
    kv("Προϊόντα shop", f"{row['active']} ενεργά, {row['variants']} μεγέθη. {row['mix']}.")
    kv("Τιμές", "Όλες συμπληρωμένες.")
    kv("Φωτο shop", "Και τα 33 προϊόντα έχουν εικόνα.")
    body(
        "Τι λείπει: dedicated σελίδα brand (όπως Core / Club4Paws). "
        "Χρειάζεται το PDF / mockup της σελίδας PROFINE, αν θέλετε ίδια παρουσίαση."
    )

    h2("5. EVERCLEAN  (EVC)")
    row = detail["EVC"]
    kv("Σελίδα brand", "ΟΧΙ — το κλικ στη μάρκα ανοίγει τον κατάλογο φιλτραρισμένο.")
    kv("Προϊόντα shop", f"{row['active']} ενεργά, {row['variants']} μεγέθη. {row['mix']}.")
    kv("Τιμές", "Όλες συμπληρωμένες.")
    kv("Φωτο shop", "Και τα 10 προϊόντα έχουν εικόνα.")
    body(
        "Τι λείπει: dedicated σελίδα brand. "
        "Χρειάζεται το PDF / mockup της σελίδας EVERCLEAN, αν θέλετε ίδια παρουσίαση."
    )

    h2("6. Wild Side  (WLD)")
    row = detail["WLD"]
    kv("Σελίδα brand", "Ναι — /products/company/WLD/  (artwork έτοιμο)")
    kv("Προϊόντα shop", "0 ενεργά. 5 προϊόντα υπάρχουν ως drafts και ΔΕΝ φαίνονται στο shop.")
    kv("Τιμές", "Και τα 9 μεγέθη είναι 0,00 €.")
    kv("SKU", "Κενά σε όλα τα μεγέθη.")
    kv("Stock", "0 σε όλα.")
    kv("Φωτο", "Τα 5 drafts έχουν εικόνα.")
    body("Προϊόντα που περιμένουν τιμές / ενεργοποίηση:")
    for product in row["inactive_list"]:
        sizes = ", ".join(
            f"{v.weight} {v.unit_label}" for v in product.variants.all()
        )
        animal = "γάτα" if product.animal_type and product.animal_type.name == "Cat" else "σκύλος"
        bullet(f"{product.name}  ({animal}, μεγέθη: {sizes})")
    body(
        "Να σταλεί: τιμές ανά μέγεθος, πραγματικά SKU, ενεργοποίηση για πώληση, "
        "και σωστό απόθεμα."
    )

    h2("7. Puro Instinto  (PUR)")
    kv("Σελίδα brand", "Ναι — /products/company/PUR/  (artwork έτοιμο)")
    kv("Προϊόντα shop", "0 — δεν υπάρχει κανένα προϊόν στη βάση.")
    kv("Τιμές", "Δεν υπάρχουν.")
    kv("Φωτο", "Δεν υπάρχουν.")
    body(
        "Τι λείπει: ολόκληρος ο κατάλογος. Να σταλεί λίστα προϊόντων (σκύλος / γάτα, "
        "ξηρά / υγρή), SKU, μεγέθη, τιμές και φωτογραφίες συσκευασίας."
    )

    h2("8. Carnis  (CAR)")
    kv("Σελίδα brand", "Ναι — /products/company/CAR/  (artwork έτοιμο)")
    kv("Προϊόντα shop", "0 — δεν υπάρχει κανένα προϊόν στη βάση.")
    kv("Τιμές", "Δεν υπάρχουν.")
    kv("Φωτο", "Δεν υπάρχουν.")
    body(
        "Τι λείπει: ολόκληρος ο κατάλογος. Να σταλεί λίστα προϊόντων (σκύλος / γάτα), "
        "SKU, μεγέθη, τιμές και φωτογραφίες συσκευασίας."
    )

    h2("9. Gaherdog / Gahercat  (δεν υπάρχει ως εταιρεία)")
    kv("Σελίδα brand", "ΟΧΙ")
    kv("Προϊόντα shop", "0 — δεν υπάρχει εγγραφή εταιρείας στη βάση.")
    body(
        "Αναφέρεται στο κείμενο «Σχετικά με εμάς» ως οικονομική σειρά, "
        "αλλά δεν υπάρχει ούτε εταιρεία ούτε προϊόντα."
    )
    body(
        "Να σταλεί, αν πωλείται: επιβεβαίωση ότι μπαίνει στο shop, κατάλογος, "
        "τιμές, φωτο, και κείμενα σελίδας."
    )

    h2("Τι να σταλεί — ανά εταιρεία")
    bullet("Carnis: προϊόντα + SKU + μεγέθη + τιμές + φωτο.")
    bullet("Puro Instinto: προϊόντα + SKU + μεγέθη + τιμές + φωτο.")
    bullet("Wild Side: τιμές, SKU, ενεργοποίηση, stock για τα 5 drafts.")
    bullet("Core: 4 φωτο Savoury Medleys (7876410, 7876420, 7876430, 7876440).")
    bullet(
        "CLUB4PAWS: SKU για Indoor 4 σε 1 αρνί (2 kg / 14 kg) και φωτο για "
        "71C1002, 86C210Μ, 86C250Μ1, 86C901 αν υπάρχουν."
    )
    bullet("PROFINE: PDF σελίδας brand, μόνο αν θέλετε dedicated σελίδα.")
    bullet("EVERCLEAN: PDF σελίδας brand, μόνο αν θέλετε dedicated σελίδα.")
    bullet("Gaherdog / Gahercat: όλος ο κατάλογος, αν θα πωλείται στο e-shop.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Saved: {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    build_pdf()
