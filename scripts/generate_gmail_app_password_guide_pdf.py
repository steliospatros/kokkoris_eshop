#!/usr/bin/env python3
"""Οδηγός Gmail App Password — τι να στείλει ο ιδιοκτήτης για τα emails του eshop."""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

OUTPUT = Path("/mnt/c/Users/steli/Downloads/Email-Gmail-Kokkoris.pdf")
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
    pdf.multi_cell(pdf.w_content, 8, "App Password Gmail — kokkorisofficial@gmail.com")
    pdf.ln(2)
    pdf.set_font("DejaVu", "", 11)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        pdf.w_content,
        6,
        "Για να φεύγουν τα emails του eshop από το δικό σου Gmail, "
        "χρειάζομαι έναν App Password. Κάνε αυτά τα βήματα εσύ "
        "στο kokkorisofficial@gmail.com και στείλε μου μόνο αυτό που λέω στο τέλος.",
    )

    pdf.step(
        1,
        "Άνοιξε το σωστό Gmail",
        [
            "1. Πήγαινε στο: https://accounts.google.com/",
            "2. Πάτα «Σύνδεση» / Sign in.",
            "3. Βάλε email: kokkorisofficial@gmail.com",
            "4. Βάλε τον κωδικό αυτού του Gmail και πάτα Επόμενο.",
            "5. Πάνω δεξιά, στο στρογγυλό εικονίδιο λογαριασμού, "
            "πρέπει να γράφει kokkorisofficial@gmail.com. "
            "Αν γράφει άλλο email, πάτα το εικονίδιο → "
            "Προσθήκη λογαριασμού / Εναλλαγή λογαριασμού και μπες σωστά.",
        ],
    )

    pdf.step(
        2,
        "Άνοιξε την ασφάλεια του λογαριασμού",
        [
            "1. Πήγαινε στο: https://myaccount.google.com/security",
            "2. Αν σου ζητήσει ξανά κωδικό, βάλτον.",
            "3. Κάνε scroll μέχρι την ενότητα «Πώς κάνετε είσοδο στον "
            "Λογαριασμό Google» / How you sign in to Google.",
            "4. Βρες τη γραμμή «Επαλήθευση σε 2 βήματα» / 2-Step Verification.",
        ],
    )

    pdf.step(
        3,
        "Άναψε την επαλήθευση σε 2 βήματα (αν είναι κλειστή)",
        [
            "Αν δίπλα γράφει Ενεργή / On, πήγαινε στο βήμα 4.",
            "",
            "Αν είναι κλειστή:",
            "1. Πάτα «Επαλήθευση σε 2 βήματα» / 2-Step Verification.",
            "2. Πάτα Έναρξη / Get started.",
            "3. Βάλε το κινητό της επιχείρησης.",
            "4. Διάλεξε SMS ή κλήση και πάτα Αποστολή.",
            "5. Γράψε τον κωδικό που ήρθε στο κινητό και πάτα Επόμενο.",
            "6. Πάτα Ενεργοποίηση / Turn on.",
            "7. Περίμενε να γράφει Ενεργή / On και γύρνα πίσω στην "
            "σελίδα Ασφάλεια.",
        ],
    )

    pdf.step(
        4,
        "Άνοιξε τους κωδικούς εφαρμογής",
        [
            "Πρώτα δοκίμασε απευθείας αυτό:",
            "https://myaccount.google.com/apppasswords",
            "",
            "Αν ανοίξει κανονικά, πήγαινε στο βήμα 5.",
            "",
            "Αν δεν ανοίγει ή λέει ότι δεν είναι διαθέσιμο:",
            "1. Πήγαινε πάλι: https://myaccount.google.com/security",
            "2. Πάτα «Επαλήθευση σε 2 βήματα» / 2-Step Verification "
            "(να μπεις μέσα στη σελίδα, όχι μόνο να τη δεις στη λίστα).",
            "3. Κάνε scroll μέχρι κάτω.",
            "4. Βρες «Κωδικοί εφαρμογών» / App passwords και πάτα το.",
            "5. Αν ζητήσει κωδικό Gmail, βάλτον ξανά.",
        ],
    )

    pdf.step(
        5,
        "Φτιάξε τον App Password",
        [
            "1. Στο πεδίο όνομα εφαρμογής / App name γράψε: Kokkoris eshop",
            "2. Πάτα Δημιουργία / Create.",
            "3. Ανοίγει παράθυρο με κωδικό 16 γραμμάτων/αριθμών, "
            "συνήθως σε 4 ομάδες, π.χ. abcd efgh ijkl mnop.",
            "4. Αντίγραψέ τον όπως είναι (με ή χωρίς κενά, δεν πειράζει).",
            "5. Κλείσε το παράθυρο μόνο αφού τον αντιγράψεις. "
            "Η Google δεν τον ξαναδείχνει.",
            "",
            "Αυτός ο 16ψήφιος είναι αυτό που θέλω εγώ. "
            "Δεν είναι ο κανονικός κωδικός του Gmail.",
        ],
    )

    pdf.step(
        6,
        "Στείλε μου αυτό",
        [
            "Στείλε μου μόνο:",
            "• τον App Password 16 χαρακτήρων από το βήμα 5",
            "• ότι τον έβγαλες από το kokkorisofficial@gmail.com",
            "",
            "Μην μου στείλεις τον κανονικό κωδικό του Gmail, "
            "κωδικό κινητού ή recovery codes. Τα βάζω εγώ μετά στο site.",
        ],
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
