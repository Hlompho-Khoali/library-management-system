import os
from datetime import date
from PIL import Image, ImageDraw, ImageFont, ImageOps
from barcode.codex import Code128


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

STATIC_DIR = os.path.join(
    BASE_DIR,
    "static"
)

CARD_DIR = os.path.join(
    STATIC_DIR,
    "cards"
)

os.makedirs(
    CARD_DIR,
    exist_ok=True
)


def format_member_number(member_id):
    return f"{member_id:08d}"


# ============================================================
# CODE 128 BARCODE
# ============================================================

CODE128_PATTERNS = [
    "11011001100", "11001101100", "11001100110",
    "10010011000", "10010001100", "10001001100",
    "10011001000", "10011000100", "10001100100",
    "11001001000", "11001000100", "11000100100",
    "10110011100", "10011011100", "10011001110",
    "10111001100", "10011101100", "10011100110",
    "11001110010", "11001011100", "11001001110",
    "11011100100", "11001110100", "11101101110",
    "11101001100", "11100101100", "11100100110",
    "11101100100", "11100110100", "11100110010",
    "11011011000", "11011000110", "11000110110",
    "10100011000", "10001011000", "10001000110",
    "10110001000", "10001101000", "10001100010",
    "11010001000", "11000101000", "11000100010",
    "10110111000", "10110001110", "10001101110",
    "10111011000", "10111000110", "10001110110",
    "11101110110", "11010001110", "11000101110",
    "11011101000", "11011100010", "11011101110",
    "11101011000", "11101000110", "11100010110",
    "11101101000", "11101100010", "11100011010",
    "11101111010", "11001000010", "11110001010",
    "10100110000", "10100001100", "10010110000",
    "10010000110", "10000101100", "10000100110",
    "10110010000", "10110000100", "10011010000",
    "10011000010", "10000110100", "10000110010",
    "11000010010", "11001010000", "11110111010",
    "11000010100", "10001111010", "10100111100",
    "10010111100", "10010011110", "10111100100",
    "10011110100", "10011110010", "11110100100",
    "11110010100", "11110010010", "11011011110",
    "11011110110", "11110110110", "10101111000",
    "10100011110", "10001011110", "10111101000",
    "10111100010", "11110101000", "11110100010",
    "10111011110", "10111000010", "11111001010",
    "11111000010", "11100101110", "10110111100",
    "10110011110", "10011011110", "10011011110",
    "11010111100", "11010011110", "11010001110",
    "11011110100", "11011110010", "11101111010",
    "11110111010", "11000110110", "11000010110",
    "11101110110"
]


def encode_code128_b(value):
    """
    Encode text using Code 128 subset B.

    Returns a binary barcode pattern.
    """

    return Code128(value).build()[0]


# ============================================================
# DRAW BARCODE
# ============================================================

def draw_barcode(
    draw,
    value,
    x,
    y,
    width,
    height
):
    """
    Draw a Code 128 barcode onto a PIL image.
    """

    pattern = encode_code128_b(
        value
    )

    module_width = width / len(pattern)

    current_x = x

    for bit in pattern:

        if bit == "1":

            draw.rectangle(
                [
                    int(current_x),
                    y,
                    int(current_x + module_width),
                    y + height
                ],
                fill="black"
            )

        current_x += module_width


# ============================================================
# FONT HELPER
# ============================================================

def get_font(size, bold=False):

    if bold:
        font_path = (
            r"C:\Windows\Fonts\arialbd.ttf"
        )
    else:
        font_path = (
            r"C:\Windows\Fonts\arial.ttf"
        )

    try:
        return ImageFont.truetype(
            font_path,
            size
        )
    except OSError:
        return ImageFont.load_default()


def add_child_footprints(image):
    footprint_path = os.path.join(
        STATIC_DIR,
        "images",
        "baby-feet.png",
    )
    if not os.path.exists(footprint_path):
        return

    footprints = Image.open(footprint_path).convert("RGBA")
    pixels = footprints.load()
    for y in range(footprints.height):
        for x in range(footprints.width):
            red, green, blue, alpha = pixels[x, y]
            if red > 90 and green > 130 and blue > 120:
                pixels[x, y] = (red, green, blue, 0)
            else:
                pixels[x, y] = (red, green, blue, min(alpha, 105))

    footprints.thumbnail((220, 190), Image.Resampling.LANCZOS)
    footprints = footprints.rotate(-35, expand=True, resample=Image.Resampling.BICUBIC)
    image.alpha_composite(
        footprints,
        (
            18,
            image.height - footprints.height - 18,
        ),
    )


# ============================================================
# GENERATE CARD
# ============================================================

def generate_virtual_card(
    member_number,
    full_name,
    library_name,
    issue_date=None,
    status_label="VALID MEMBER",
    status_fill="white",
    status_text_color=(18, 64, 48),
    child_card=False,
):
    """
    Generate a virtual library membership card.

    The card expires exactly one year after issue.
    """

    if issue_date is None:
        issue_date = date.today()

    expiry_date = issue_date.replace(
        year=issue_date.year + 1
    )

    # --------------------------------------------------------
    # Card dimensions
    # --------------------------------------------------------

    width = 1000
    height = 630

    image = Image.new(
        "RGBA",
        (width, height),
        "white"
    )

    if child_card:
        add_child_footprints(image)

    draw = ImageDraw.Draw(
        image
    )

    # --------------------------------------------------------
    # Fonts
    # --------------------------------------------------------

    title_font = get_font(
        42,
        bold=True
    )

    subtitle_font = get_font(
        24,
        bold=True
    )

    name_font = get_font(
        38,
        bold=True
    )

    normal_font = get_font(
        24
    )

    small_font = get_font(
        20
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    draw.rectangle(
        [0, 0, width, 135],
        fill=(18, 64, 48)
    )

    draw.text(
        (50, 25),
        "TSHWANE LIBRARY",
        font=title_font,
        fill="white"
    )

    draw.text(
        (52, 82),
        "DIGITAL MEMBERSHIP CARD",
        font=subtitle_font,
        fill=(220, 190, 80)
    )

    # City of Tshwane logo badge
    logo_path = os.path.join(
        STATIC_DIR,
        "images",
        "tshwane icon.jpg"
    )
    badge_size = 96
    badge_left = width - badge_size - 34
    badge_top = 20
    badge = Image.new("RGB", (badge_size, badge_size), "white")
    badge_mask = Image.new("L", (badge_size, badge_size), 0)
    ImageDraw.Draw(badge_mask).ellipse(
        [0, 0, badge_size - 1, badge_size - 1],
        fill=255
    )

    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGB")
        logo.thumbnail((badge_size - 12, badge_size - 12), Image.Resampling.LANCZOS)
        logo_left = (badge_size - logo.width) // 2
        logo_top = (badge_size - logo.height) // 2
        badge.paste(logo, (logo_left, logo_top))

    image.paste(badge, (badge_left, badge_top), badge_mask)
    draw.ellipse(
        [badge_left, badge_top, badge_left + badge_size - 1, badge_top + badge_size - 1],
        outline=(220, 190, 80),
        width=3
    )

    # --------------------------------------------------------
    # Member information
    # --------------------------------------------------------

    draw.text(
        (55, 175),
        "MEMBER",
        font=small_font,
        fill=(90, 90, 90)
    )

    draw.text(
        (55, 205),
        full_name.upper(),
        font=name_font,
        fill=(20, 20, 20)
    )

    draw.text(
        (55, 280),
        "MEMBER NUMBER",
        font=small_font,
        fill=(90, 90, 90)
    )

    draw.text(
        (55, 310),
        member_number,
        font=subtitle_font,
        fill=(20, 20, 20)
    )

    # --------------------------------------------------------
    # Library
    # --------------------------------------------------------

    draw.text(
        (55, 370),
        "LIBRARY",
        font=small_font,
        fill=(90, 90, 90)
    )

    draw.text(
        (55, 400),
        library_name,
        font=subtitle_font,
        fill=(20, 20, 20)
    )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    draw.text(
        (55, 460),
        "ISSUED",
        font=small_font,
        fill=(90, 90, 90)
    )

    draw.text(
        (55, 490),
        issue_date.strftime("%d %b %Y"),
        font=normal_font,
        fill=(20, 20, 20)
    )

    draw.text(
        (280, 460),
        "EXPIRES",
        font=small_font,
        fill=(90, 90, 90)
    )

    draw.text(
        (280, 490),
        expiry_date.strftime("%d %b %Y"),
        font=normal_font,
        fill=(20, 20, 20)
    )

    # --------------------------------------------------------
    # Barcode
    # --------------------------------------------------------

    barcode_x = 560
    barcode_y = 190
    barcode_width = 380
    barcode_height = 190

    draw_barcode(
        draw,
        member_number,
        barcode_x,
        barcode_y,
        barcode_width,
        barcode_height
    )

    # Barcode number
    barcode_font = get_font(
        22,
        bold=True
    )

    bbox = draw.textbbox(
        (0, 0),
        member_number,
        font=barcode_font
    )

    text_width = bbox[2] - bbox[0]

    draw.text(
        (
            barcode_x
            + (barcode_width - text_width) / 2,
            barcode_y + barcode_height + 15
        ),
        member_number,
        font=barcode_font,
        fill="black"
    )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    draw.rectangle(
        [560, 500, 940, 555],
        outline=(18, 64, 48),
        fill=status_fill,
        width=2
    )

    draw.text(
        (650, 515),
        status_label,
        font=normal_font,
        fill=status_text_color
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    filename = (
        f"{member_number}.png"
    )

    file_path = os.path.join(
        CARD_DIR,
        filename
    )

    image.save(
        file_path,
        "PNG"
    )

    return {
        "file_path": file_path,
        "filename": filename,
        "issue_date": issue_date,
        "expiry_date": expiry_date
    }