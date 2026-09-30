from app.services.ocr_service import extract_id_information


image_path = (
    r"C:\Users\hlomp\OneDrive\Desktop"
    r"\library-management-system"
    r"\app\static\images\id_example.png"
)


result = extract_id_information(image_path)


print("\n==============================")
print("OCR RESULT")
print("==============================")

print("Surname:", result["surname"])
print("Names:", result["names"])
print("ID Number:", result["id_number"])
print("ID Valid:", result["id_valid"])
print("Date of Birth:", result["date_of_birth"])