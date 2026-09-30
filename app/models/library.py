from app.extensions import db


class Library(db.Model):
    __tablename__ = "libraries"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(150),
        nullable=False,
        unique=True
    )

    region_id = db.Column(
        db.Integer,
        db.ForeignKey("regions.id"),
        nullable=False
    )

    region = db.relationship(
        "Region",
        back_populates="libraries"
    )

    members = db.relationship(
        "Member",
        back_populates="library"
    )

    def __repr__(self):
        return f"<Library {self.name}>"