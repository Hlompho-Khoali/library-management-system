from app.extensions import db


class Region(db.Model):
    __tablename__ = "regions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)

    libraries = db.relationship(
        "Library",
        back_populates="region",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Region {self.name}>"