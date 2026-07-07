#!/usr/bin/env python3
"""Generate neutral question-list PDF for Kokkoris — saved to Downloads."""
from pathlib import Path

from fpdf import FPDF

OUTPUT = Path("/mnt/c/Users/steli/Downloads/Kokkoris_Eshop_Stoicheia_kai_Kimena.pdf")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

SECTIONS = [
    (
        "1. Πληροφορίες για το κατάστημα",
        [
            "Διεύθυνση καταστήματος / έδρας;",
            "Ωράριο λειτουργίας;",
            "Κείμενο παρουσίασης της εταιρείας;",
            "Φωτογραφίες καταστήματος (αν υπάρχουν);",
        ],
    ),
    (
        "2. Επικοινωνία",
        [
            "Τηλέφωνο επικοινωνίας;",
            "Email επικοινωνίας;",
            "Ώρες εξυπηρέτησης;",
            "Link Facebook;",
            "Link Instagram;",
            "Link website;",
        ],
    ),
    (
        "3. Τρόποι αποστολής & χρόνος παραλαβής",
        [
            "Παράδοση με όχημα εταιρείας — ναι/όχι; σε ποιες περιοχές;",
            "Παράδοση με courier — ναι/όχι; ποιος συνεργάτης;",
            "Εκτιμώμενος χρόνος παράδοσης εντός Αθήνας;",
            "Εκτιμώμενος χρόνος παράδοσης εκτός Αθήνας / νησιά;",
            "Ελάχιστη παραγγελία;",
        ],
    ),
    (
        "4. Κόστος αποστολής",
        [
            "Κόστος παράδοσης με όχημα εταιρείας;",
            "Κόστος courier (ανά ζώνη / βάρος / Τ.Κ.);",
            "Δωρεάν μεταφορικά από ποιο ποσό;",
            "Ειδικές χρεώσεις (νησιά, βαρέα δέματα κλπ.);",
        ],
    ),
    (
        "5. Πολιτική επιστροφών",
        [
            "Ημέρες δικαιώματος επιστροφής;",
            "Προϊόντα που εξαιρούνται;",
            "Μεταφορικά επιστροφής — ποιος τα καλύπτει;",
            "Διαδικασία επιστροφής χρημάτων;",
            "Τηλέφωνο / email για αιτήματα επιστροφής;",
        ],
    ),
    (
        "6. Τρόποι πληρωμής",
        [
            "Αντικαταβολή — ναι/όχι; επιπλέον χρέωση;",
            "Πληρωμή με κάρτα online — ναι/όχι;",
            "Τραπεζική κατάθεση — ναι/όχι; IBAN;",
            "Άλλοι τρόποι πληρωμής;",
        ],
    ),
    (
        "7. Πολιτική απορρήτου",
        [
            "Υπάρχει έτοιμο κείμενο;",
            "Ειδικές σημειώσεις για χρήση δεδομένων πελατών;",
        ],
    ),
    (
        "8. Επιπλέον",
        [
            "Αποθέματα (stock) προϊόντων;",
            "Logo Carnis;",
            "Κείμενα σελίδων μαρκών (Puro Instinto, Wild Side, Carnis κλπ.);",
        ],
    ),
]


class ChecklistPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", size=9)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"{self.page_no()}/{{nb}}", align="C")


def build_pdf():
    pdf = ChecklistPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_font("DejaVu", "", FONT)
    pdf.add_font("DejaVuB", "", FONT_BOLD)
    pdf.add_page()
    w = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("DejaVuB", size=15)
    pdf.set_text_color(30, 80, 72)
    pdf.multi_cell(w, 8, "Kokkoris Pet Food — e-shop")
    pdf.set_font("DejaVuB", size=12)
    pdf.multi_cell(w, 7, "Στοιχεία & κείμενα για τις σελίδες πληροφοριών")
    pdf.ln(6)

    for title, questions in SECTIONS:
        if pdf.get_y() > 250:
            pdf.add_page()

        pdf.set_font("DejaVuB", size=11)
        pdf.set_text_color(30, 80, 72)
        pdf.multi_cell(w, 7, title)
        pdf.ln(1)

        pdf.set_font("DejaVu", size=10)
        pdf.set_text_color(40, 40, 40)
        for q in questions:
            pdf.multi_cell(w, 6, f"  •  {q}")

        pdf.ln(2)
        pdf.set_draw_color(220, 220, 220)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.l_margin + w, y)
        pdf.ln(5)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
