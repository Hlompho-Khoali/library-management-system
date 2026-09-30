import unittest
from datetime import date
import os

from app import create_app
from app.extensions import db
from app.models import Library, Member, Region


class ChildMembershipTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        region = Region(name="Test Region")
        library = Library(name="Test Library", region=region)
        self.parent = Member(
            title="Ms",
            first_name="Parent",
            last_name="User",
            id_number="9001010000001",
            date_of_birth=date(1990, 1, 1),
            phone_number="0821234567",
            street_address="1 Main Road",
            suburb="Central",
            city="Pretoria",
            postal_code="0001",
            library=library,
            email="parent@example.com",
            password_hash="hashed-password",
            id_review_status="approved",
            id_verified=True,
        )
        db.session.add(self.parent)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_parent_can_create_child_membership(self):
        with self.client.session_transaction() as session:
            session["member_id"] = self.parent.id
            session["role"] = "member"

        response = self.client.post("/member/add-child", data={
            "first_name": "Child",
            "middle_name": "",
            "last_name": "User",
            "date_of_birth": "2017-05-20",
        })

        self.assertEqual(response.status_code, 302)
        child = Member.query.filter_by(parent_id=self.parent.id).one()
        self.assertTrue(child.is_child)
        self.assertTrue(child.id_verified)
        self.assertEqual(child.library_id, self.parent.library_id)

        dashboard = self.client.get("/member/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Child virtual card", dashboard.data)
        self.assertIn(b"Child User", dashboard.data)
        self.assertTrue(
            os.path.exists(f"app/static/cards/{child.id:08d}.png")
        )

        edit_response = self.client.post(
            f"/member/child/{child.id}/edit",
            data={
                "first_name": "Updated",
                "middle_name": "",
                "last_name": "User",
                "date_of_birth": "2017-05-20",
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        self.assertEqual(Member.query.get(child.id).first_name, "Updated")

        delete_response = self.client.post(f"/member/child/{child.id}/delete")
        self.assertEqual(delete_response.status_code, 302)
        self.assertIsNone(db.session.get(Member, child.id))


if __name__ == "__main__":
    unittest.main()
