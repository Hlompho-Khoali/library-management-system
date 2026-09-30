import io
import re
from datetime import date

import pytesseract

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# ============================================================
# SOUTH AFRICAN ID VALIDATION
# ============================================================

def validate_sa_id(id_number):
    """
    Validate the structure and checksum of a South African ID.
    """

    if not id_number:
        return False

    id_number = re.sub(r"\D", "", id_number)

    if len(id_number) != 13:
        return False

    # --------------------------------------------------------
    # Validate YYMMDD
    # --------------------------------------------------------

    yy = id_number[0:2]
    mm = id_number[2:4]
    dd = id_number[4:6]

    try:
        year = int(yy)
        month = int(mm)
        day = int(dd)

        if month < 1 or month > 12:
            return False

        if day < 1 or day > 31:
            return False

    except ValueError:
        return False

    # --------------------------------------------------------
    # Citizenship/status digit
    # --------------------------------------------------------

    if id_number[10] not in {"0", "1"}:
        return False

    # --------------------------------------------------------
    # Luhn checksum
    # --------------------------------------------------------

    digits = [int(d) for d in id_number]

    total = sum(digits[::2])

    doubled_digits = []

    for digit in digits[1::2]:
        value = digit * 2

        if value > 9:
            value -= 9

        doubled_digits.append(value)

    total += sum(doubled_digits)

    return total % 10 == 0


# ============================================================
# CONVERT ID DATE TO YYYY-MM-DD
# ============================================================

def date_from_sa_id(id_number):
    """
    Extract the date of birth from the first six digits
    of a South African ID number.

    Example:
        0210025992087
        -> 02 October 2002
        -> 2002-10-02
    """

    if not id_number or len(id_number) != 13:
        return None

    try:
        yy = int(id_number[0:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])

        current_year = date.today().year
        current_two_digits = current_year % 100

        # Determine century.
        if yy <= current_two_digits:
            year = 2000 + yy
        else:
            year = 1900 + yy

        birth_date = date(
            year,
            month,
            day
        )

        return birth_date.strftime("%Y-%m-%d")

    except ValueError:
        return None


# ============================================================
# PREPARE FIELD
# ============================================================

def prepare_field(crop):

    crop = crop.resize(
        (
            crop.width * 5,
            crop.height * 5
        )
    )

    gray = ImageOps.grayscale(crop)

    gray = ImageOps.autocontrast(gray)

    gray = ImageEnhance.Contrast(
        gray
    ).enhance(2.5)

    gray = gray.filter(
        ImageFilter.SHARPEN
    )

    return gray


# ============================================================
# OCR FIELD
# ============================================================

def ocr_field(image, whitelist):

    results = []

    for psm in [6, 7, 8, 11, 13]:

        config = (
            f"--psm {psm} "
            f"-c tessedit_char_whitelist={whitelist}"
        )

        text = pytesseract.image_to_string(
            image,
            config=config
        ).strip()

        if text:
            results.append(text)

    return results


# ============================================================
# EXTRACT ID NUMBER
# ============================================================

def extract_id_number(image):

    width, height = image.size

    scale_x = width / 916
    scale_y = height / 580

    id_crop = image.crop(
        (
            int(220 * scale_x),
            int(350 * scale_y),
            int(620 * scale_x),
            int(410 * scale_y)
        )
    )

    candidates = []

    # --------------------------------------------------------
    # Normal OCR
    # --------------------------------------------------------

    processed = prepare_field(id_crop)

    candidates.extend(
        ocr_field(
            processed,
            "0123456789"
        )
    )

    # --------------------------------------------------------
    # Threshold 100
    # --------------------------------------------------------

    threshold_image = ImageOps.grayscale(
        id_crop.resize(
            (
                id_crop.width * 5,
                id_crop.height * 5
            )
        )
    )

    threshold_image = ImageOps.autocontrast(
        threshold_image
    )

    threshold_image = threshold_image.point(
        lambda pixel: 255 if pixel > 100 else 0
    )

    candidates.extend(
        ocr_field(
            threshold_image,
            "0123456789"
        )
    )

    # --------------------------------------------------------
    # Look for valid 13-digit numbers
    # --------------------------------------------------------

    valid_candidates = []

    for text in candidates:

        matches = re.findall(
            r"\d{13}",
            text
        )

        for match in matches:

            if validate_sa_id(match):
                valid_candidates.append(match)

    # Remove duplicates
    valid_candidates = list(
        dict.fromkeys(valid_candidates)
    )

    if valid_candidates:
        return valid_candidates[0]

    return None


# ============================================================
# EXTRACT DATE OF BIRTH FROM OCR
# ============================================================

def extract_date_of_birth_ocr(image):

    width, height = image.size

    scale_x = width / 916
    scale_y = height / 580

    dob_crop = image.crop(
        (
            int(220 * scale_x),
            int(395 * scale_y),
            int(620 * scale_x),
            int(455 * scale_y)
        )
    )

    candidates = []

    # --------------------------------------------------------
    # Normal OCR
    # --------------------------------------------------------

    processed = prepare_field(dob_crop)

    candidates.extend(
        ocr_field(
            processed,
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )
    )

    # --------------------------------------------------------
    # Threshold 100
    # --------------------------------------------------------

    threshold_image = ImageOps.grayscale(
        dob_crop.resize(
            (
                dob_crop.width * 5,
                dob_crop.height * 5
            )
        )
    )

    threshold_image = ImageOps.autocontrast(
        threshold_image
    )

    threshold_image = threshold_image.point(
        lambda pixel: 255 if pixel > 100 else 0
    )

    candidates.extend(
        ocr_field(
            threshold_image,
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )
    )

    # --------------------------------------------------------
    # Search for DDMMMYYYY
    # --------------------------------------------------------

    for text in candidates:

        cleaned = re.sub(
            r"[^A-Z0-9]",
            "",
            text.upper()
        )

        match = re.search(
            r"(\d{2})"
            r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
            r"(\d{4})",
            cleaned
        )

        if match:

            day = match.group(1)
            month = match.group(2)
            year = match.group(3)

            months = {
                "JAN": "01",
                "FEB": "02",
                "MAR": "03",
                "APR": "04",
                "MAY": "05",
                "JUN": "06",
                "JUL": "07",
                "AUG": "08",
                "SEP": "09",
                "OCT": "10",
                "NOV": "11",
                "DEC": "12"
            }

            month_number = months[month]

            try:
                birth_date = date(
                    int(year),
                    int(month_number),
                    int(day)
                )

                return birth_date.strftime(
                    "%Y-%m-%d"
                )

            except ValueError:
                pass

    return None


# ============================================================
# EXTRACT NAMES
# ============================================================

def extract_names(image):
    """
    Extract surname and names from dedicated ID-card regions.
    """

    width, height = image.size

    scale_x = width / 916
    scale_y = height / 580

    # ========================================================
    # SURNAME
    # ========================================================

    surname_crop = image.crop(
        (
            int(235 * scale_x),
            int(155 * scale_y),
            int(560 * scale_x),
            int(190 * scale_y)
        )
    )

    surname_processed = prepare_field(
        surname_crop
    )

    surname_results = ocr_field(
        surname_processed,
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    )

    surname = None

    for text in surname_results:

        cleaned = re.sub(
            r"[^A-Za-z\s'-]",
            " ",
            text
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned
        ).strip()

        words = cleaned.split()

        if words:
            surname = words[0].upper()
            break

    # ========================================================
    # NAMES
    # ========================================================

    names_crop = image.crop(
        (
            int(235 * scale_x),
            int(200 * scale_y),
            int(600 * scale_x),
            int(230 * scale_y)
        )
    )

    # --------------------------------------------------------
    # Try several processing methods
    # --------------------------------------------------------

    candidates = []

    # Normal
    processed = prepare_field(
        names_crop
    )

    candidates.extend(
        ocr_field(
            processed,
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        )
    )

    # Threshold 100
    threshold = ImageOps.grayscale(
        names_crop.resize(
            (
                names_crop.width * 5,
                names_crop.height * 5
            )
        )
    )

    threshold = ImageOps.autocontrast(
        threshold
    )

    threshold = threshold.point(
        lambda pixel: 255 if pixel > 100 else 0
    )

    candidates.extend(
        ocr_field(
            threshold,
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        )
    )

    # ========================================================
    # CLEAN NAME CANDIDATES
    # ========================================================

    cleaned_candidates = []

    for text in candidates:

        cleaned = re.sub(
            r"[^A-Za-z\s'-]",
            " ",
            text
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned
        ).strip()

        if not cleaned:
            continue

        words = cleaned.split()

        # Remove obviously tiny OCR fragments.
        words = [
            word
            for word in words
            if len(word) >= 3
        ]

        if len(words) >= 2:

            candidate = " ".join(
                word.upper()
                for word in words
            )

            cleaned_candidates.append(
                candidate
            )

    # ========================================================
    # SELECT BEST CANDIDATE
    # ========================================================

    names = None

    # Prefer exactly two words.
    two_word_candidates = [
        candidate
        for candidate in cleaned_candidates
        if len(candidate.split()) == 2
    ]

    if two_word_candidates:

        # Prefer the candidate with reasonable word lengths.
        for candidate in two_word_candidates:

            words = candidate.split()

            if (
                3 <= len(words[0]) <= 15
                and
                3 <= len(words[1]) <= 15
            ):
                names = candidate
                break

    # If there wasn't an exact two-word result,
    # use the shortest sensible multi-word result.
    if not names and cleaned_candidates:

        names = min(
            cleaned_candidates,
            key=lambda value: len(value)
        )

    return surname, names


# ============================================================
# COMPARISON AGAINST REGISTRATION DATA
# ============================================================

def normalize_name(value):
    if value is None:
        return ""

    return re.sub(
        r"[^A-Za-z]",
        "",
        str(value).upper()
    )


def compare_registration_to_ocr(registration, extracted):
    """
    Compare the OCR result from the uploaded ID with the data the
    member entered during registration.
    """

    if not registration:
        return {
            "matches": False,
            "reason": "Registration data is missing."
        }

    if not extracted:
        return {
            "matches": False,
            "reason": "The ID image could not be read."
        }

    if not extracted.get("id_valid", False):
        return {
            "matches": False,
            "reason": "The ID number on the uploaded document is not valid."
        }

    registration_id = re.sub(r"\D", "", str(registration.get("id_number", "")))
    extracted_id = re.sub(r"\D", "", str(extracted.get("id_number", "")))

    if registration_id and extracted_id and registration_id != extracted_id:
        return {
            "matches": False,
            "reason": "ID number does not match the uploaded ID document."
        }

    registration_dob = str(registration.get("date_of_birth", "")).strip()
    extracted_dob = str(extracted.get("date_of_birth", "")).strip()

    if registration_dob and extracted_dob and registration_dob != extracted_dob:
        return {
            "matches": False,
            "reason": "Date of birth does not match the uploaded ID document."
        }

    extracted_last_name = normalize_name(
        extracted.get("last_name") or extracted.get("surname") or ""
    )
    extracted_first_name = normalize_name(
        extracted.get("first_name") or ""
    )
    extracted_middle_name = normalize_name(
        extracted.get("middle_name") or ""
    )

    if not extracted_first_name and extracted.get("names"):
        names = str(extracted.get("names")).strip()
        name_parts = names.split()

        if name_parts:
            extracted_first_name = normalize_name(name_parts[0])

        if len(name_parts) > 1:
            extracted_middle_name = normalize_name(" ".join(name_parts[1:-1]))

        if len(name_parts) > 1 and not extracted_last_name:
            extracted_last_name = normalize_name(name_parts[-1])

    registration_first_name = normalize_name(registration.get("first_name", ""))
    registration_middle_name = normalize_name(registration.get("middle_name", ""))
    registration_last_name = normalize_name(registration.get("last_name", ""))

    if registration_first_name and extracted_first_name and registration_first_name != extracted_first_name:
        return {
            "matches": False,
            "reason": "First name does not match the uploaded ID document."
        }

    if registration_middle_name and extracted_middle_name and registration_middle_name != extracted_middle_name:
        return {
            "matches": False,
            "reason": "Middle name does not match the uploaded ID document."
        }

    if registration_last_name and extracted_last_name and registration_last_name != extracted_last_name:
        return {
            "matches": False,
            "reason": "Surname does not match the uploaded ID document."
        }

    return {
        "matches": True,
        "reason": "ID matches registration details."
    }


# ============================================================
# MAIN OCR FUNCTION
# ============================================================

def extract_id_information_from_bytes(image_bytes):
    image = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    surname, names = extract_names(image)
    id_number = extract_id_number(image)
    date_of_birth = extract_date_of_birth_ocr(image)

    id_valid = False

    if id_number:
        id_valid = validate_sa_id(id_number)

    if id_valid:
        id_date_of_birth = date_from_sa_id(id_number)

        if id_date_of_birth:
            date_of_birth = id_date_of_birth

    return {
        "surname": surname,
        "names": names,
        "first_name": names.split()[0].upper() if names and names.split() else None,
        "middle_name": " ".join(names.split()[1:-1]).upper() if names and len(names.split()) > 2 else None,
        "last_name": surname.upper() if surname else None,
        "id_number": id_number,
        "id_valid": id_valid,
        "date_of_birth": date_of_birth,
    }


def extract_id_information(image_path):

    with Image.open(
        image_path
    ) as image:
        image = image.convert("RGB")

    # --------------------------------------------------------
    # Extract surname + names
    # --------------------------------------------------------

    surname, names = extract_names(
        image
    )

    # --------------------------------------------------------
    # Extract ID number
    # --------------------------------------------------------

    id_number = extract_id_number(
        image
    )

    # --------------------------------------------------------
    # Extract DOB directly from DOB field
    # --------------------------------------------------------

    date_of_birth = extract_date_of_birth_ocr(
        image
    )

    # --------------------------------------------------------
    # Validate ID
    # --------------------------------------------------------

    id_valid = False

    if id_number:
        id_valid = validate_sa_id(
            id_number
        )

    # --------------------------------------------------------
    # If OCR DOB is bad/missing, derive DOB from
    # the validated ID number.
    #
    # This gives us a reliable fallback.
    # --------------------------------------------------------

    if id_valid:

        id_date_of_birth = date_from_sa_id(
            id_number
        )

        if id_date_of_birth:

            date_of_birth = id_date_of_birth

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "surname": surname,
        "names": names,
        "id_number": id_number,
        "id_valid": id_valid,
        "date_of_birth": date_of_birth
    }