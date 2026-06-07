from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
import os

CARD_DIR = "uploads/cards"
os.makedirs(CARD_DIR, exist_ok=True)


def generate_membership_card(volunteer, qr_path):

    pdf_path = os.path.join(
        CARD_DIR,
        f"{volunteer.registration_no}-membership-card.pdf"
    )

    WIDTH = 650
    HEIGHT = 400

    c = canvas.Canvas(
        pdf_path,
        pagesize=(WIDTH, HEIGHT)
    )

    # ==========================
    # BACKGROUND
    # ==========================

    c.setFillColorRGB(0.05, 0.23, 0.14)
    c.rect(0, 0, WIDTH, HEIGHT, fill=1)

    # Gold Header

    c.setFillColorRGB(0.83, 0.69, 0.22)
    c.rect(0, 350, WIDTH, 50, fill=1)

    # White Card Body

    c.setFillColorRGB(1, 1, 1)
    c.roundRect(
        20,
        20,
        WIDTH - 40,
        HEIGHT - 90,
        15,
        fill=1
    )

    # ==========================
    # TITLE
    # ==========================

    c.setFillColor(colors.black)

    c.setFont(
        "Helvetica-Bold",
        18
    )

    c.drawCentredString(
        WIDTH / 2,
        365,
        "EX-IGP ADAMU YOUTH VOLUNTEERS"
    )

    c.setFont(
        "Helvetica-Bold",
        14
    )

    c.drawCentredString(
        WIDTH / 2,
        335,
        "OFFICIAL MEMBERSHIP CARD"
    )

    # ==========================
    # PASSPORT
    # ==========================

    if (
        volunteer.passport
        and
        os.path.exists(volunteer.passport)
    ):
        c.drawImage(
            volunteer.passport,
            40,
            120,
            width=130,
            height=150,
            preserveAspectRatio=True,
            mask="auto"
        )

    # ==========================
    # DETAILS
    # ==========================

    c.setFillColor(colors.black)

    c.setFont(
        "Helvetica-Bold",
        10
    )

    details_x = 200

    c.drawString(
        details_x,
        280,
        "Membership No:"
    )

    c.drawString(
        details_x,
        250,
        "Full Name:"
    )

    c.drawString(
        details_x,
        220,
        "Gender:"
    )

    c.drawString(
        details_x,
        190,
        "LGA:"
    )

    c.drawString(
        details_x,
        160,
        "Ward:"
    )

    c.drawString(
        details_x,
        130,
        "Unit:"
    )

    c.drawString(
        details_x,
        100,
        "Joined:"
    )

    c.setFont(
        "Helvetica",
        10
    )

    c.drawString(
        310,
        280,
        volunteer.registration_no or ""
    )

    c.drawString(
        310,
        250,
        volunteer.name or ""
    )

    c.drawString(
        310,
        220,
        volunteer.gender or ""
    )

    c.drawString(
        310,
        190,
        volunteer.lga or ""
    )

    c.drawString(
        310,
        160,
        volunteer.ward or ""
    )

    c.drawString(
        310,
        130,
        volunteer.unit or ""
    )

    c.drawString(
        310,
        100,
        datetime.now().strftime(
            "%d %B %Y"
        )
    )

    # ==========================
    # STATUS
    # ==========================

    c.setFillColorRGB(
        0,
        0.5,
        0
    )

    c.setFont(
        "Helvetica-Bold",
        14
    )

    c.drawString(
        200,
        60,
        "STATUS: ACTIVE"
    )

    # ==========================
    # QR CODE
    # ==========================

    if qr_path and os.path.exists(qr_path):
        c.drawImage(
            qr_path,
            500,
            60,
            width=90,
            height=90,
            preserveAspectRatio=True,
            mask="auto"
        )

    # ==========================
    # FOOTER
    # ==========================

    c.setFillColor(colors.grey)

    c.setFont(
        "Helvetica",
        8
    )

    c.drawCentredString(
        WIDTH / 2,
        35,
        "Official Membership Card"
    )

    c.save()

    return pdf_path