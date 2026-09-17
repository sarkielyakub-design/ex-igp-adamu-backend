from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from datetime import datetime
from PIL import Image
import os


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

CARD_DIR = os.path.join(
    BASE_DIR,
    "uploads",
    "cards"
)

ASSET_DIR = os.path.join(
    BASE_DIR,
    "assets"
)

BACKGROUND_PATH = os.path.join(
    ASSET_DIR,
    "card_background.png"
)

os.makedirs(CARD_DIR, exist_ok=True)


# ============================================================
# HELPER: DRAW CROPPED IMAGE
# ============================================================

def draw_cropped_image(
    c,
    image_path,
    x,
    y,
    width,
    height
):
    """
    Draw an image inside a fixed box while cropping
    excess parts so the image completely fills the box.
    """

    try:
        image = Image.open(image_path).convert("RGB")

        image_width, image_height = image.size

        target_ratio = width / height
        image_ratio = image_width / image_height

        if image_ratio > target_ratio:
            # Image is wider -> crop left/right
            new_width = int(
                image_height * target_ratio
            )

            left = (
                image_width - new_width
            ) // 2

            image = image.crop(
                (
                    left,
                    0,
                    left + new_width,
                    image_height
                )
            )

        else:
            # Image is taller -> crop top/bottom
            new_height = int(
                image_width / target_ratio
            )

            top = (
                image_height - new_height
            ) // 2

            image = image.crop(
                (
                    0,
                    top,
                    image_width,
                    top + new_height
                )
            )

        temp_path = os.path.join(
            CARD_DIR,
            "_temp_passport.jpg"
        )

        image.save(
            temp_path,
            "JPEG",
            quality=95
        )

        c.drawImage(
            ImageReader(temp_path),
            x,
            y,
            width=width,
            height=height,
            preserveAspectRatio=False,
            mask="auto"
        )

        try:
            os.remove(temp_path)
        except Exception:
            pass

    except Exception as e:
        print(
            f"Passport image error: {e}"
        )


# ============================================================
# MEMBERSHIP CARD GENERATOR
# ============================================================

def generate_membership_card(
    volunteer,
    qr_path
):

    # ========================================================
    # PDF PATH
    # ========================================================

    pdf_path = os.path.join(
        CARD_DIR,
        f"{volunteer.registration_no}-membership-card.pdf"
    )

    # ========================================================
    # CARD SIZE
    # Same aspect ratio as the supplied template
    # ========================================================

    WIDTH = 650
    HEIGHT = 400

    c = canvas.Canvas(
        pdf_path,
        pagesize=(WIDTH, HEIGHT)
    )

    # ========================================================
    # BACKGROUND TEMPLATE
    # ========================================================

    if os.path.exists(BACKGROUND_PATH):

        c.drawImage(
            ImageReader(BACKGROUND_PATH),
            0,
            0,
            width=WIDTH,
            height=HEIGHT,
            preserveAspectRatio=False,
            mask="auto"
        )

    else:

        # Fallback if background is missing
        c.setFillColorRGB(
            0.02,
            0.30,
            0.16
        )

        c.rect(
            0,
            0,
            WIDTH,
            HEIGHT,
            fill=1,
            stroke=0
        )

        print(
            f"WARNING: Card background not found: "
            f"{BACKGROUND_PATH}"
        )

    # ========================================================
    # PASSPORT PHOTO
    # ========================================================
    #
    # Position matches the left photo area of the template.
    #

    if (
        getattr(volunteer, "passport", None)
        and
        os.path.exists(volunteer.passport)
    ):

        draw_cropped_image(
            c,
            volunteer.passport,
            55,
            118,
            120,
            145
        )

    # ========================================================
    # QR CODE
    # ========================================================
    #
    # The template already contains the QR frame.
    # We place the real QR code inside it.
    #

    if (
        qr_path
        and
        os.path.exists(qr_path)
    ):

        c.drawImage(
            ImageReader(qr_path),
            505,
            62,
            width=88,
            height=88,
            preserveAspectRatio=True,
            mask="auto"
        )

    # ========================================================
    # COLORS
    # ========================================================

    GREEN = colors.HexColor(
        "#087A3E"
    )

    DARK_GREEN = colors.HexColor(
        "#064D2B"
    )

    BLACK = colors.HexColor(
        "#111111"
    )

    GOLD = colors.HexColor(
        "#D9B53F"
    )

    # ========================================================
    # DETAILS POSITION
    # ========================================================

    label_x = 205
    value_x = 315

    y = 285
    gap = 28

    # ========================================================
    # LABELS
    # ========================================================

    c.setFillColor(
        colors.HexColor("#666666")
    )

    c.setFont(
        "Helvetica",
        9
    )

    c.drawString(
        label_x,
        y,
        "MEMBERSHIP NO"
    )

    c.drawString(
        label_x,
        y - gap,
        "FULL NAME"
    )

    c.drawString(
        label_x,
        y - gap * 2,
        "GENDER"
    )

    c.drawString(
        label_x,
        y - gap * 3,
        "LGA"
    )

    c.drawString(
        label_x,
        y - gap * 4,
        "WARD"
    )

    c.drawString(
        label_x,
        y - gap * 5,
        "UNIT"
    )

    c.drawString(
        label_x,
        y - gap * 6,
        "JOINED"
    )

    # ========================================================
    # VALUES
    # ========================================================

    c.setFillColor(
        BLACK
    )

    c.setFont(
        "Helvetica-Bold",
        11
    )

    c.drawString(
        value_x,
        y,
        str(
            volunteer.registration_no
            or ""
        )
    )

    c.setFont(
        "Helvetica-Bold",
        12
    )

    c.drawString(
        value_x,
        y - gap,
        str(
            volunteer.name
            or ""
        ).upper()
    )

    c.setFont(
        "Helvetica",
        10
    )

    c.drawString(
        value_x,
        y - gap * 2,
        str(
            volunteer.gender
            or ""
        )
    )

    c.drawString(
        value_x,
        y - gap * 3,
        str(
            volunteer.lga
            or ""
        )
    )

    c.drawString(
        value_x,
        y - gap * 4,
        str(
            volunteer.ward
            or ""
        )
    )

    c.drawString(
        value_x,
        y - gap * 5,
        str(
            volunteer.unit
            or ""
        )
    )

    # ========================================================
    # JOINED DATE
    # ========================================================

    created_at = getattr(
        volunteer,
        "created_at",
        None
    )

    if created_at:

        joined = created_at.strftime(
            "%d %B %Y"
        )

    else:

        joined = datetime.now().strftime(
            "%d %B %Y"
        )

    c.drawString(
        value_x,
        y - gap * 6,
        joined
    )

    # ========================================================
    # STATUS
    # ========================================================

    c.setFillColor(
        GREEN
    )

    c.setFont(
        "Helvetica-Bold",
        14
    )

    c.drawString(
        205,
        70,
        "STATUS: ACTIVE"
    )

    # ========================================================
    # FOOTER
    # ========================================================

    c.setFillColor(
        colors.HexColor("#777777")
    )

    c.setFont(
        "Helvetica",
        7
    )

    c.drawCentredString(
        WIDTH / 2,
        22,
        "Official Membership Card"
    )

    # ========================================================
    # SAVE PDF
    # ========================================================

    c.save()

    print(
        f"Membership card generated: {pdf_path}"
    )

    return pdf_path