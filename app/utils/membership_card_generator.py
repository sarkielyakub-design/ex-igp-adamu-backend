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
    # =====================================================
    # BACKGROUND
    # =====================================================

    background = "assets/card_background.png"

    if os.path.exists(background):
        c.drawImage(
            ImageReader(background),
            0,
            0,
            width=WIDTH,
            height=HEIGHT,
            preserveAspectRatio=False,
            mask="auto",
        )
    else:
        c.setFillColorRGB(0.05, 0.23, 0.14)
        c.rect(0, 0, WIDTH, HEIGHT, fill=1)

    # =====================================================
    # PASSPORT PHOTO
    # =====================================================

    if volunteer.passport and os.path.exists(volunteer.passport):
        c.drawImage(
            volunteer.passport,
            55,
            118,
            width=120,
            height=145,
            preserveAspectRatio=True,
            mask="auto",
        )

    # =====================================================
    # QR CODE
    # =====================================================

    if qr_path and os.path.exists(qr_path):
        c.drawImage(
            qr_path,
            515,
            60,
            width=75,
            height=75,
            preserveAspectRatio=True,
            mask="auto",
        )

    # =====================================================
    # DETAILS
    # =====================================================

    label_x = 205
    value_x = 315
    y = 285
    gap = 28

    c.setFillColor(colors.black)

    c.setFont("Helvetica-Bold", 10)

    c.drawString(label_x, y, "Membership No:")
    c.drawString(label_x, y-gap, "Full Name:")
    c.drawString(label_x, y-gap*2, "Gender:")
    c.drawString(label_x, y-gap*3, "LGA:")
    c.drawString(label_x, y-gap*4, "Ward:")
    c.drawString(label_x, y-gap*5, "Unit:")
    c.drawString(label_x, y-gap*6, "Joined:")

    c.setFont("Helvetica", 10)

    c.drawString(value_x, y, volunteer.registration_no or "")
    c.drawString(value_x, y-gap, volunteer.name or "")
    c.drawString(value_x, y-gap*2, volunteer.gender or "")
    c.drawString(value_x, y-gap*3, volunteer.lga or "")
    c.drawString(value_x, y-gap*4, volunteer.ward or "")
    c.drawString(value_x, y-gap*5, volunteer.unit or "")

    joined = (
        volunteer.created_at.strftime("%d %B %Y")
        if getattr(volunteer, "created_at", None)
        else datetime.now().strftime("%d %B %Y")
    )

    c.drawString(value_x, y-gap*6, joined)

    # =====================================================
    # STATUS
    # =====================================================

    c.setFillColorRGB(0.0, 0.55, 0.0)
    c.setFont("Helvetica-Bold", 16)

    c.drawString(
        205,
        70,
        "STATUS: ACTIVE"
    )

    # =====================================================
    # FOOTER
    # =====================================================

    c.setFillColor(colors.grey)

    c.setFont(
        "Helvetica",
        8
    )

    c.drawCentredString(
        WIDTH / 2,
        22,
        "Official Membership Card"
    )
    c.save()

    return pdf_path