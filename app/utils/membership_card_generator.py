from datetime import datetime
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


# ============================================================
# PATHS
# ============================================================

# /app/app/utils/membership_card_generator.py -> /app/app
APP_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = APP_DIR / "uploads"
CARD_DIR = UPLOADS_DIR / "cards"

CARD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def resolve_upload_path(path: str | Path | None) -> Path | None:
    """Resolve absolute, uploads-relative, or /uploads/ paths."""

    if not path:
        return None

    value = str(path).replace("\\", "/")
    candidate = Path(value)

    if candidate.is_absolute():
        return candidate

    if value.startswith("/uploads/"):
        return APP_DIR / value.lstrip("/")

    if value.startswith("uploads/"):
        return APP_DIR / value

    return APP_DIR / value


def draw_cropped_image(
    c: canvas.Canvas,
    image_path: str | Path,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float = 8,
) -> None:
    """Draw a passport image cropped to exactly fill the target box."""

    path = resolve_upload_path(image_path)

    if not path or not path.exists():
        return

    try:
        with Image.open(path) as source:
            image = source.convert("RGB")
            image_width, image_height = image.size

            target_ratio = width / height
            image_ratio = image_width / image_height

            if image_ratio > target_ratio:
                new_width = int(image_height * target_ratio)
                left = (image_width - new_width) // 2
                image = image.crop(
                    (left, 0, left + new_width, image_height)
                )
            else:
                new_height = int(image_width / target_ratio)
                top = (image_height - new_height) // 2
                image = image.crop(
                    (0, top, image_width, top + new_height)
                )

            temp_path = CARD_DIR / "_temp_passport.jpg"
            image.save(temp_path, "JPEG", quality=95)

        c.setStrokeColor(colors.HexColor("#0B6B3A"))
        c.setLineWidth(2)
        c.roundRect(
            x - 2, y - 2, width + 4, height + 4,
            radius, stroke=1, fill=0
        )

        c.drawImage(
            ImageReader(str(temp_path)),
            x, y, width=width, height=height,
            preserveAspectRatio=False,
            mask="auto",
        )

        try:
            temp_path.unlink()
        except OSError:
            pass

    except Exception as exc:
        print(f"Passport image error: {exc}")


def draw_text_fit(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_name: str = "Helvetica-Bold",
    font_size: float = 11,
    min_size: float = 7,
) -> None:
    """Draw text and reduce its size when the value is too long."""

    value = str(text or "")
    size = font_size

    while (
        size > min_size
        and c.stringWidth(value, font_name, size) > max_width
    ):
        size -= 0.5

    c.setFont(font_name, size)
    c.drawString(x, y, value)


def draw_label_value(
    c: canvas.Canvas,
    label: str,
    value: str,
    y: float,
    label_x: float,
    value_x: float,
    value_width: float,
) -> None:
    """Draw one clean membership-card detail row."""

    c.setFillColor(colors.HexColor("#667085"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(label_x, y, label)

    c.setStrokeColor(colors.HexColor("#D0D5DD"))
    c.setLineWidth(0.6)
    c.line(value_x, y - 2, value_x + value_width, y - 2)

    draw_text_fit(
        c, value, value_x, y, value_width,
        "Helvetica-Bold", 10.5, 7
    )


# ============================================================
# MEMBERSHIP CARD GENERATOR
# ============================================================

def generate_membership_card(
    volunteer,
    qr_path: str | Path | None,
) -> str:
    """
    Generate the EX-IGP Adamu Youth Volunteer membership card.

    This version draws the card directly with ReportLab and does
    not depend on the old card_background.png template.
    """

    registration_no = str(
        getattr(volunteer, "registration_no", "") or ""
    )

    pdf_path = CARD_DIR / (
        f"{registration_no}-membership-card.pdf"
    )

    # ========================================================
    # CARD SIZE
    # ========================================================

    WIDTH = 650
    HEIGHT = 400

    c = canvas.Canvas(
        str(pdf_path),
        pagesize=(WIDTH, HEIGHT),
    )

    # ========================================================
    # COLORS
    # ========================================================

    GREEN = colors.HexColor("#087A3E")
    DARK_GREEN = colors.HexColor("#064D2B")
    LIGHT_GREEN = colors.HexColor("#EAF6EF")
    GOLD = colors.HexColor("#D9B53F")
    DARK = colors.HexColor("#111827")
    GRAY = colors.HexColor("#667085")
    BORDER = colors.HexColor("#D9E2DC")
    WHITE = colors.white

    # ========================================================
    # CARD BASE
    # ========================================================

    c.setFillColor(WHITE)
    c.roundRect(
        0, 0, WIDTH, HEIGHT, 14,
        stroke=0, fill=1
    )

    # ========================================================
    # HEADER
    # ========================================================

    c.setFillColor(DARK_GREEN)
    c.roundRect(
        0, HEIGHT - 105, WIDTH, 105, 14,
        stroke=0, fill=1
    )

    c.rect(
        0, HEIGHT - 105, WIDTH, 14,
        stroke=0, fill=1
    )

    c.setFillColor(GOLD)
    c.rect(
        0, HEIGHT - 108, WIDTH, 3,
        stroke=0, fill=1
    )

    # ========================================================
    # ORGANISATION MARK
    # ========================================================

    logo_x = 48
    logo_y = HEIGHT - 54

    c.setFillColor(GOLD)
    c.circle(logo_x, logo_y, 30, stroke=0, fill=1)

    c.setFillColor(DARK_GREEN)
    c.circle(logo_x, logo_y, 25, stroke=0, fill=1)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(logo_x, logo_y + 5, "EX")

    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(logo_x, logo_y - 7, "IGP")

    # ========================================================
    # HEADER TITLE
    # ========================================================

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(92, HEIGHT - 45, "EX-IGP ADAMU")

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(92, HEIGHT - 68, "YOUTH VOLUNTEERS")

    c.setFillColor(WHITE)
    c.setFont("Helvetica", 7.5)
    c.drawString(
        93, HEIGHT - 88,
        "VOLUNTEER MEMBERSHIP CARD"
    )

    # Slogan.
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 7.5)

    c.drawRightString(
        WIDTH - 35, HEIGHT - 42,
        "SERVICE TO HUMANITY"
    )
    c.drawRightString(
        WIDTH - 35, HEIGHT - 56,
        "SAFER COMMUNITIES"
    )
    c.drawRightString(
        WIDTH - 35, HEIGHT - 70,
        "BRIGHTER TOMORROW"
    )

    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(
        WIDTH - 160, HEIGHT - 79,
        WIDTH - 35, HEIGHT - 79
    )

    # ========================================================
    # MAIN BODY
    # ========================================================

    c.setFillColor(colors.HexColor("#F8FAF9"))
    c.rect(
        0, 0, WIDTH, HEIGHT - 110,
        stroke=0, fill=1
    )

    # Header stays visually above body.
    c.setFillColor(DARK_GREEN)
    c.rect(
        0, HEIGHT - 105, WIDTH, 5,
        stroke=0, fill=1
    )

    # ========================================================
    # PHOTO
    # ========================================================

    photo_x = 38
    photo_y = 108
    photo_w = 145
    photo_h = 175

    c.setFillColor(WHITE)
    c.roundRect(
        photo_x - 7, photo_y - 7,
        photo_w + 14, photo_h + 14,
        10, stroke=0, fill=1
    )

    passport_path = resolve_upload_path(
        getattr(volunteer, "passport", None)
    )

    if passport_path and passport_path.exists():
        draw_cropped_image(
            c,
            passport_path,
            photo_x,
            photo_y,
            photo_w,
            photo_h,
            8,
        )
    else:
        c.setFillColor(colors.HexColor("#E5E7EB"))
        c.roundRect(
            photo_x, photo_y,
            photo_w, photo_h,
            8, stroke=0, fill=1
        )

        c.setFillColor(GRAY)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(
            photo_x + photo_w / 2,
            photo_y + photo_h / 2,
            "PHOTO"
        )

    c.setFillColor(GREEN)
    c.roundRect(
        photo_x, photo_y - 31,
        photo_w, 23, 6,
        stroke=0, fill=1
    )

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(
        photo_x + photo_w / 2,
        photo_y - 23,
        "VOLUNTEER"
    )

    # ========================================================
    # MEMBER DETAILS
    # ========================================================

    details_x = 215
    label_x = details_x
    value_x = 310
    value_width = 185

    start_y = 284
    row_gap = 29

    created_at = getattr(volunteer, "created_at", None)

    joined = (
        created_at.strftime("%d %B %Y")
        if created_at
        else datetime.now().strftime("%d %B %Y")
    )

    rows = [
        ("MEMBERSHIP NO.", registration_no),
        (
            "FULL NAME",
            str(getattr(volunteer, "name", "") or "").upper()
        ),
        (
            "GENDER",
            str(getattr(volunteer, "gender", "") or "")
        ),
        (
            "LGA",
            str(getattr(volunteer, "lga", "") or "")
        ),
        (
            "WARD",
            str(getattr(volunteer, "ward", "") or "")
        ),
        (
            "UNIT",
            str(getattr(volunteer, "unit", "") or "")
        ),
        ("JOINED", joined),
    ]

    for index, (label, value) in enumerate(rows):
        draw_label_value(
            c,
            label,
            value,
            start_y - row_gap * index,
            label_x,
            value_x,
            value_width,
        )

    # ========================================================
    # STATUS
    # ========================================================

    status_y = 72

    c.setFillColor(LIGHT_GREEN)
    c.roundRect(
        details_x, status_y,
        150, 27, 7,
        stroke=0, fill=1
    )

    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(
        details_x + 75,
        status_y + 9,
        "STATUS: ACTIVE"
    )

    # ========================================================
    # QR CODE
    # ========================================================

    qr_x = 520
    qr_y = 93
    qr_size = 92

    c.setFillColor(WHITE)
    c.roundRect(
        qr_x - 8, qr_y - 8,
        qr_size + 16, qr_size + 16,
        8, stroke=0, fill=1
    )

    c.setStrokeColor(GREEN)
    c.setLineWidth(1.5)
    c.roundRect(
        qr_x - 8, qr_y - 8,
        qr_size + 16, qr_size + 16,
        8, stroke=1, fill=0
    )

    qr_file = resolve_upload_path(qr_path)

    if qr_file and qr_file.exists():
        c.drawImage(
            ImageReader(str(qr_file)),
            qr_x, qr_y,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )

    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(
        qr_x + qr_size / 2,
        qr_y - 21,
        "SCAN TO VERIFY"
    )

    # ========================================================
    # FOOTER
    # ========================================================

    c.setStrokeColor(BORDER)
    c.setLineWidth(0.7)
    c.line(35, 40, WIDTH - 35, 40)

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(
        WIDTH / 2, 24,
        "Official Membership Card"
    )

    # ========================================================
    # FINAL BORDER
    # ========================================================

    c.setStrokeColor(colors.HexColor("#0B6B3A"))
    c.setLineWidth(1.5)
    c.roundRect(
        1, 1,
        WIDTH - 2, HEIGHT - 2,
        14, stroke=1, fill=0
    )

    c.save()

    print(f"Membership card generated: {pdf_path}")

    return str(pdf_path)
