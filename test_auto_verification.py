import unittest

from app.services.ocr_service import compare_registration_to_ocr


class AutoVerificationTests(unittest.TestCase):
    def test_matching_registration_and_ocr_data_passes(self):
        registration = {
            "first_name": "Jane",
            "middle_name": "Grace",
            "last_name": "Doe",
            "id_number": "0102034567084",
            "date_of_birth": "2001-02-03",
        }

        extracted = {
            "first_name": "JANE",
            "middle_name": "GRACE",
            "last_name": "DOE",
            "id_number": "0102034567084",
            "date_of_birth": "2001-02-03",
            "id_valid": True,
        }

        result = compare_registration_to_ocr(registration, extracted)

        self.assertTrue(result["matches"])
        self.assertEqual(result["reason"], "ID matches registration details.")

    def test_mismatched_id_number_fails(self):
        registration = {
            "first_name": "Jane",
            "last_name": "Doe",
            "id_number": "0102034567084",
            "date_of_birth": "2001-02-03",
        }

        extracted = {
            "first_name": "Jane",
            "last_name": "Doe",
            "id_number": "0102034567085",
            "date_of_birth": "2001-02-03",
            "id_valid": True,
        }

        result = compare_registration_to_ocr(registration, extracted)

        self.assertFalse(result["matches"])
        self.assertIn("ID number", result["reason"])


if __name__ == "__main__":
    unittest.main()
