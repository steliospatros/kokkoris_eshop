#!/usr/bin/env python3
"""Οδηγός BOX NOW — αναλυτικά βήματα, μόνο ό,τι χρειάζεται από BOX NOW."""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

OUTPUT = Path("/mnt/c/Users/steli/Downloads/BoxNow-Απλος-Οδηγος-Kokkoris.pdf")
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
    pdf.multi_cell(pdf.w_content, 8, "BOX NOW — Kokkoris eshop")
    pdf.ln(3)
    pdf.set_font("DejaVu", "", 11)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        pdf.w_content,
        6,
        "Εγώ φτιάχνω το site. Χρειάζομαι από εσένα την επαφή με την BOX NOW "
        "και τα στοιχεία λογαριασμού που θα σου δώσουν. "
        "Τα URLs API, webhooks και τεχνικές ρυθμίσεις τα κάνω εγώ.",
    )

    pdf.step(
        1,
        "Άνοιξε τη φόρμα επικοινωνίας",
        [
            "Πήγαινε στο: https://boxnow.gr/get-in-touch",
            "Άνοιξε τη σελίδα από υπολογιστή ή κινητό.",
        ],
    )

    pdf.step(
        2,
        "Συμπλήρωσε τα στοιχεία της επιχείρησης",
        [
            "Επωνυμία: Kokkoris Pet Food (ή όπως είναι νομικά).",
            "ΑΦΜ, διεύθυνση, email, τηλέφωνο επικοινωνίας.",
            "Διεύθυνση αποθήκης/καταστήματος από όπου θα μαζεύουν τα δέματα.",
            "Τηλέφωνο υπεύθυνου που θα έχει πρόσβαση στο σύστημα BOX NOW (SMS OTP).",
            "Αν έχουν πολλά σημεία αποστολής, γράψε όλα.",
        ],
    )

    pdf.step(
        3,
        "Γράψε στο μήνυμα της φόρμας",
        [
            "Αντίγραψε και στείλε αυτό:",
            "",
            "«Θέλουμε να γίνουμε συνεργάτες για ηλεκτρονικό κατάστημα (eshop). "
            "Χρειαζόμαστε Partner ID, OAuth Client ID και Client Secret, "
            "και Location ID για το σημείο αποστολής. "
            "Ο τεχνικός υπεύθυνος του site θα κάνει την ενσωμάτωση.»",
        ],
    )

    pdf.step(
        4,
        "Στείλε τη φόρμα και κράτα το email επιβεβαίωσης",
        [
            "Πάτα αποστολή.",
            "Κράτα screenshot ή forward το email που θα σου έρθει.",
            "Η BOX NOW συνήθως απαντά σε μερικές εργάσιμες ημέρες.",
        ],
    )

    pdf.step(
        5,
        "Αν δεν απαντήσουν σε 5–7 εργάσιμες",
        [
            "Στείλε email σε sales@boxnow.gr",
            "ή σε ict@boxnow.gr",
            "Γράψε ότι έχεις ήδη στείλει αίτημα και περιμένεις Partner API credentials.",
        ],
    )

    pdf.step(
        6,
        "Όταν σου απαντήσουν — στείλε ΜΟΝΟ αυτά σε μένα",
        [
            "Partner ID (αριθμός συνεργάτη — για χάρτη locker στο site)",
            "OAuth Client ID",
            "OAuth Client Secret",
            "Origin Location ID (αριθμός σημείου αποστολής / αποθήκης)",
            "Webhook secret (αν στο email/PDF το αναφέρουν)",
            "Τιμές ανά θήκη locker από το συμβόλαιό σας (μικρή / μεσαία / μεγάλη σε €)",
            "Αν τα credentials είναι για δοκιμή (sandbox) ή για live (production)",
            "",
            "Δεν χρειάζεται να μου στείλεις API URLs, οδηγίες webhook ή τεχνικά manuals — "
            "τα έχω ήδη.",
        ],
    )

    pdf.step(
        7,
        "Αν σε ρωτήσουν «ποιο URL να βάλουμε για webhook»",
        [
            "Μην το ψάχνεις μόνος σου. Στείλε μου το email και θα σου πω ακριβώς "
            "τι URL να τους δώσεις (εξαρτάται από το domain του site).",
        ],
    )

    pdf.step(
        8,
        "Τέλος",
        [
            "Μόλις μου στείλεις τα στοιχεία του βήματος 6, τα βάζω εγώ στο site.",
            "Σου λέω όταν να κάνουμε δοκιμαστική παραγγελία με locker.",
        ],
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
