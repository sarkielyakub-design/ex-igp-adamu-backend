from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
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
    # BACKGROUND IMAGE
    # ==========================

    background = "assets/card_background.png"

    if os.path.exists(background):
        c.drawImage(
            ImageReader(background),
            0,
            0,
            width=WIDTH,
            height=HEIGHT,
            preserveAspectRatio=False,
            mask="auto"
        )
    else:
        c.setFillColorRGB(0.05, 0.23, 0.14)
        c.rect(0, 0, WIDTH, HEIGHT, fill=1)

    # ==========================
    # PASSPORT PHOTO
    # ==========================

    if volunteer.passport and os.path.exists(volunteer.passport):
        c.drawImage(
            volunteer.passport,
            45,
            115,
            width=120,
            height=145,
            preserveAspectRatio=True,
            mask="auto"
        )

    # ==========================
    # QR CODE
    # ==========================

    if qr_path and os.path.exists(qr_path):
        c.drawImage(
            qr_path,
            500,
            65,
            width=85,
            height=85,
            preserveAspectRatio=True,
            mask="auto"
        )

    # ==========================
    # DETAILS
    # ==========================

    details_x = 205

    c.setFillColor(colors.black)

    c.setFont("Helvetica-Bold", 10)

    c.drawString(details_x, 285, "Membership No:")
    c.drawString(details_x, 255, "Full Name:")
    c.drawString(details_x, 225, "Gender:")
    c.drawString(details_x, 195, "LGA:")
    c.drawString(details_x, 165, "Ward:")
    c.drawString(details_x, 135, "Unit:")
    c.drawString(details_x, 105, "Joined:")

    c.setFont("Helvetica", 10)

    c.drawString(315, 285, volunteer.registration_no or "")
    c.drawString(315, 255, volunteer.name or "")
    c.drawString(315, 225, volunteer.gender or "")
    c.drawString(315, 195, volunteer.lga or "")
    c.drawString(315, 165, volunteer.ward or "")
    c.drawString(315, 135, volunteer.unit or "")
    c.drawString(
        315,
        105,
        datetime.now().strftime("%d %B %Y")
    )

    # ==========================
    # STATUS
    # ==========================

    c.setFillColor(colors.green)
    c.setFont("Helvetica-Bold", 16)

    c.drawString(
        205,
        70,
        "STATUS: ACTIVE"
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
        30,
        "Official Membership Card"
    )

    c.save()

    return pdf_path