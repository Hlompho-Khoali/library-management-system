from app import create_app
from app.extensions import db
from app.models import Region, Library


LIBRARIES = {
    "Region 1 – Soshanguve, Mabopane, Ga-Rankuwa & Winterveld": [
        "Mabopane Library",
        "Bodibeng Library",
        "Ga-Rankuwa Library",
        "Winterveld Library",
        "Mabopane Block X Library",
        "Soshanguve Library",
    ],

    "Region 2 – Hammanskraal/Temba": [
        "Hammanskraal Library",
        "Temba Library",
    ],

    "Region 3 – Pretoria Central, Atteridgeville & surrounding areas": [
        "Es’kia Mphahlele Community Library",
        "New Atteridgeville Library",
        "Atteridgeville Library",
        "Brooklyn Community Library",
        "Mayville Library",
        "Moot Library",
        "Waverley Community Library",
        "Pretoria City Library",
    ],

    "Region 4 – Centurion, Valhalla, Laudium & surrounding areas": [
        "Valhalla Library",
        "Eldoraigne Library",
        "Pierre van Ryneveld Library",
        "Lyttelton Library",
        "Laudium Library",
        "Olievenhoutbosch Library",
    ],

    "Region 5 – Cullinan, Rayton & surrounding areas": [
        "Cullinan Library",
        "Rayton Library",
        "Roodeplaat Library",
        "Refilwe Community Library",
    ],

    "Region 6 – Mamelodi, Eersterust & surrounding areas": [
        "Eersterust Library",
        "Stanza Bopape Library",
        "Mamelodi Library",
        "Nellmapius Community Library",
        "Silverton Library",
        "Garsfontein Library",
        "Glenstantia Library",
    ],

    "Region 7 – Bronkhorstspruit & surrounding areas": [
        "Zithobeni Library",
        "Rethabiseng Community Library",
        "Ekangala Library",
        "Sokhulumi Library",
        "Bronkhorstspruit Library",
    ],
}


def seed_database():
    app = create_app()

    with app.app_context():
        for region_name, library_names in LIBRARIES.items():

            region = Region.query.filter_by(name=region_name).first()

            if region is None:
                region = Region(name=region_name)
                db.session.add(region)
                db.session.flush()

            for library_name in library_names:

                library = Library.query.filter_by(
                    name=library_name
                ).first()

                if library is None:
                    library = Library(
                        name=library_name,
                        region_id=region.id
                    )
                    db.session.add(library)

        db.session.commit()

        print("Library database seeded successfully.")

        print(f"Regions: {Region.query.count()}")
        print(f"Libraries: {Library.query.count()}")


if __name__ == "__main__":
    seed_database()