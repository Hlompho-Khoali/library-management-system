import re

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

image_path = (
    r"C:\Users\hlomp\OneDrive\Desktop\library-management-system"
    r"\app\static\images\id_example.png"
)

image = Image.open(image_path).convert("RGB")


# ============================================================
# OCR HELPER
# ============================================================

def run_ocr(image, whitelist, label):

    print(f"\n--- {label} ---")

    for psm in [6, 7, 8, 11, 13]:

        config = (
            f"--psm {psm} "
            f"-c tessedit_char_whitelist={whitelist}"
        )

        text = pytesseract.image_to_string(
            image,
            config=config
        ).strip()

        print(
            f"PSM {psm}: {repr(text)}"
        )


# ============================================================
# PREPARE FIELD
# ============================================================

def prepare_field(crop):

    # Make the field much larger
    crop = crop.resize(
        (
            crop.width * 4,
            crop.height * 4
        )
    )

    # Convert to grayscale
    gray = ImageOps.grayscale(crop)

    # Increase contrast
    gray = ImageOps.autocontrast(gray)

    gray = ImageEnhance.Contrast(
        gray
    ).enhance(2.5)

    # Sharpen
    gray = gray.filter(
        ImageFilter.SHARPEN
    )

    return gray


# ============================================================
# ID NUMBER REGION
# ============================================================

print("\n==============================")
print("IDENTITY NUMBER TEST")
print("==============================")

# The number is directly underneath "Identity Number"
id_crop = image.crop(
    (
        220,
        350,
        620,
        410
    )
)

id_processed = prepare_field(
    id_crop
)

run_ocr(
    id_processed,
    "0123456789",
    "ID NUMBER - NORMAL"
)


# ============================================================
# THRESHOLD TESTS
# ============================================================

print("\n==============================")
print("ID NUMBER THRESHOLD TESTS")
print("==============================")

gray = ImageOps.grayscale(
    id_crop.resize(
        (
            id_crop.width * 5,
            id_crop.height * 5
        )
    )
)

gray = ImageOps.autocontrast(gray)


for threshold in [100, 120, 140, 160, 180, 200]:

    threshold_image = gray.point(
        lambda pixel: 255 if pixel > threshold else 0
    )

    run_ocr(
        threshold_image,
        "0123456789",
        f"THRESHOLD {threshold}"
    )


# ============================================================
# DATE OF BIRTH
# ============================================================

print("\n==============================")
print("DATE OF BIRTH TEST")
print("==============================")

dob_crop = image.crop(
    (
        220,
        395,
        620,
        455
    )
)

dob_processed = prepare_field(
    dob_crop
)

run_ocr(
    dob_processed,
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "DOB - NORMAL"
)


# ============================================================
# DOB THRESHOLD TESTS
# ============================================================

print("\n==============================")
print("DOB THRESHOLD TESTS")
print("==============================")

gray = ImageOps.grayscale(
    dob_crop.resize(
        (
            dob_crop.width * 5,
            dob_crop.height * 5
        )
    )
)

gray = ImageOps.autocontrast(gray)


for threshold in [100, 120, 140, 160, 180, 200]:

    threshold_image = gray.point(
        lambda pixel: 255 if pixel > threshold else 0
    )

    run_ocr(
        threshold_image,
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        f"DOB THRESHOLD {threshold}"
    )