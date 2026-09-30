import unittest
from datetime import date

from app import create_app
from app.extensions import db
from app.models import Verification
from app.services.approval_service import create_member_from_verification


class AdminReviewFlowTests(unittest.TestCase):
    def test_faq_is_available_and_linked_from_home(self):
        app = create_app({
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
        })

        with app.app_context():
            db.create_all()

        client = app.test_client()
        faq_response = client.get("/faq")
        home_response = client.get("/")

        self.assertEqual(faq_response.status_code, 200)
        self.assertIn(b"Frequently asked questions", faq_response.data)
        self.assertIn(b"href=\"/faq\"", home_response.data)

    def test_privacy_notice_is_available_and_registration_requires_consent(self):
        app = create_app({
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
        })

        with app.app_context():
            db.create_all()

        client = app.test_client()
        notice_response = client.get("/privacy-consent")
        registration_response = client.post("/register", data={})

        self.assertEqual(notice_response.status_code, 200)
        self.assertIn(b"POPIA privacy notice", notice_response.data)
        self.assertEqual(registration_response.status_code, 200)
        self.assertIn(b"Please read and accept", registration_response.data)

    def test_create_member_from_verification_activates_member(self):
        app = create_app({
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
        })

        with app.app_context():
            db.create_all()

            verification = Verification(
                title="Mr",
                first_name="Jane",
                middle_name="Grace",
                last_name="Doe",
                id_number="0102034567084",
                date_of_birth=date(2001, 2, 3),
                phone_number="0821234567",
                street_address="1 Main Road",
                suburb="Soshanguve",
                city="Pretoria",
                postal_code="0001",
                library_id=1,
                email="jane@example.com",
                password_hash="hashed-password",
                id_document_path="pending/test.jpg",
                status="pending",
            )
            db.session.add(verification)
            db.session.commit()

            member = create_member_from_verification(verification)

            self.assertEqual(member.first_name, "Jane")
            self.assertTrue(member.is_active)
            self.assertTrue(member.id_verified)
            self.assertEqual(member.role, "member")


if __name__ == "__main__":
    unittest.main()

