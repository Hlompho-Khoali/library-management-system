import pytesseract
from PIL import Image
from pytesseract import Output

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

image_path = r"C:\Users\hlomp\OneDrive\Desktop\library-management-system\app\static\images\id_example.png"

image = Image.open(image_path)

configs = [
    "--psm 6",
    "--psm 11",
    "--psm 12"
]

for config in configs:

    print("\n")
    print("=" * 70)
    print(f"OCR MODE: {config}")
    print("=" * 70)

    data = pytesseract.image_to_data(
        image,
        config=config,
        output_type=Output.DICT
    )

    for i in range(len(data["text"])):

        text = data["text"][i].strip()

        if not text:
            continue

        confidence = float(data["conf"][i])

        # Ignore extremely low-confidence noise
        if confidence < 20:
            continue

        x = data["left"][i]
        y = data["top"][i]
        width = data["width"][i]
        height = data["height"][i]

        print(
            f"TEXT: {text:<25} "
            f"X: {x:<4} "
            f"Y: {y:<4} "
            f"W: {width:<4} "
            f"H: {height:<4} "
            f"CONF: {confidence:.1f}"
        )