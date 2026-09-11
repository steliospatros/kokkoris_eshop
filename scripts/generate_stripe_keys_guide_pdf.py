#!/usr/bin/env python3
"""Οδηγός Stripe κλειδιών — τι να στείλει ο ιδιοκτήτης για live πληρωμές."""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

OUTPUT = Path("/mnt/c/Users/steli/Downloads/Stripe-Pliromes-Kokkoris.pdf")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


class GuidePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", FONT)
        self.add_font("DejaVu", "B", FONT_BOLD)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    @property
    def w_content(self):
        return self.w - self.l_margin - self.r_margin

    def step(self, number: int, title: str, lines: list[str]):
        self.ln(5)
        self.set_font("DejaVu", "B", 12)
        self.set_x(self.l_margin)
        self.multi_cell(self.w_content, 7, f"Βήμα {number} — {title}")
        self.set_font("DejaVu", "", 11)
        for line in lines:
            if line == "":
                self.ln(2)
                continue
            self.set_x(self.l_margin)
            self.multi_cell(self.w_content, 6, line)
        self.ln(2)


def build_pdf() -> Path:
    pdf = GuidePDF()
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.w_content, 8, "Πληρωμές με κάρτα — Kokkoris eshop")
    pdf.ln(3)
    pdf.set_font("DejaVu", "", 11)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        pdf.w_content,
        6,
        "Εγώ φτιάχνω το site. Για να πάνε τα λεφτά των online πληρωμών "
        "στον επαγγελματικό λογαριασμό της επιχείρησης (όχι σε μένα), "
        "χρειάζομαι τα live κλειδιά Stripe του λογαριασμού σας. "
        "IBAN, e-banking και κωδικούς τράπεζας δεν τα θέλω — "
        "η τράπεζα συνδέεται μέσα στο Stripe, από εσάς.",
    )

    pdf.step(
        1,
        "Άνοιξε το Stripe Dashboard",
        [
            "Πήγαινε στο: https://dashboard.stripe.com/login",
            "Συνδέσου με τον επαγγελματικό λογαριασμό πληρωμών της επιχείρησης.",
            "Αν δεν θυμάσαι αν έχετε Stripe: πες μου ποιο σύστημα πληρωμών "
            "έχετε ήδη (Stripe, Viva.com, POS τράπεζας κλπ.). "
            "Το σημερινό site δουλεύει με Stripe.",
        ],
    )

    pdf.step(
        2,
        "Βεβαιώσου ότι είσαι σε Live, όχι Test",
        [
            "Πάνω δεξιά (ή στο switch Test / Live) επίλεξε Live.",
            "Τα κλειδιά πρέπει να αρχίζουν με pk_live_ και sk_live_.",
            "Αν αρχίζουν με pk_test_ / sk_test_, είναι δοκιμαστικά — "
            "με αυτά δεν μπαίνουν πραγματικά λεφτά.",
        ],
    )

    pdf.step(
        3,
        "Πάρε τα δύο κλειδιά",
        [
            "Πήγαινε: Developers → API keys",
            "ή απευθείας: https://dashboard.stripe.com/apikeys",
            "",
            "Αντίγραψε:",
            "• Publishable key  (αρχίζει με pk_live_…)",
            "• Secret key      (αρχίζει με sk_live_…  — πάτα Reveal / Reveal live key)",
            "",
            "Αν σου προτείνει Restricted key (rk_live_…), είναι επίσης εντάξει.",
        ],
    )

    pdf.step(
        4,
        "Έλεγχος ότι ο λογαριασμός είναι έτοιμος για πραγματικές πληρωμές",
        [
            "Στο Dashboard πρέπει να φαίνεται ότι ολοκληρώθηκε η επαλήθευση "
            "της επιχείρησης (στοιχεία, ΑΦΜ, ταυτότητα).",
            "Πρέπει να είναι συνδεδεμένος τραπεζικός λογαριασμός (IBAN) "
            "για τις εκταμιεύσεις — αυτό το κάνεις εσύ μέσα στο Stripe, "
            "όχι στο site.",
            "Αν κάτι λείπει, το Stripe θα σου δείξει τι να συμπληρώσεις. "
            "Μην στείλεις τα κλειδιά πριν τελειώσει αυτό.",
        ],
    )

    pdf.step(
        5,
        "Στείλε ΜΟΝΟ αυτά σε μένα",
        [
            "Publishable key  (pk_live_…)",
            "Secret key       (sk_live_… ή rk_live_…)",
            "Επιβεβαίωση ότι ο λογαριασμός είναι Live / ενεργοποιημένος.",
            "",
            "Το webhook (η «γέφυρα» πληρωμής → παραγγελία στο site) "
            "το φτιάχνουμε μαζί όταν ανέβει το site στον πραγματικό τομέα. "
            "Μην το ρυθμίσεις μόνος σου.",
        ],
    )

    pdf.step(
        6,
        "Πώς να τα στείλεις (σημαντικό)",
        [
            "Το Secret key είναι σαν κωδικός ταμείου. Όποιος το έχει, "
            "μπορεί να κινεί πληρωμές του λογαριασμού.",
            "Μην το στείλεις σε Messenger, SMS, Facebook ή ανοιχτό email "
            "αν γίνεται να το αποφύγεις.",
            "Καλύτερα: από κοντά, ή μέσω password manager / κρυπτογραφημένο μήνυμα.",
            "Αν το έστειλες κατά λάθος σε ανοιχτό κανάλι, πήγαινε στο Stripe "
            "και κάνε Roll / Rotate το secret key — μετά στείλε μου το καινούργιο.",
        ],
    )

    pdf.step(
        7,
        "Τι ΔΕΝ χρειάζεται να μου στείλεις",
        [
            "IBAN ή κωδικούς e-banking.",
            "PIN κάρτας, κωδικό Stripe login (αρκούν τα κλειδιά).",
            "Συμβόλαια τράπεζας ή POS manuals.",
        ],
    )

    pdf.step(
        8,
        "Τέλος",
        [
            "Μόλις μου στείλεις τα κλειδιά του βήματος 5, τα βάζω εγώ στο site.",
            "Τα λεφτά από κάρτα πάνε στον δικό σας Stripe / τράπεζα, "
            "όχι σε εμένα.",
            "Η αντικαταβολή στο κατάστημα μένει όπως είναι — δεν περνάει από Stripe.",
        ],
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
