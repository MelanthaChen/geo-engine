from sqlalchemy.orm import Session

from app.models.property import Property


DEFAULT_PROPERTY = {
    "name": "GeoAIResume",
    "domain": "geoairesume-web-six.vercel.app",
    "brand_name": "GeoAIResume",
    "description": "Default GEO Engine property.",
}

LEGACY_DEFAULT_DOMAINS = {
    "geoairesume.com",
}


def normalize_property_domain(domain: str):
    normalized = domain.strip()

    if normalized.startswith("https://"):
        normalized = normalized.removeprefix("https://")

    if normalized.startswith("http://"):
        normalized = normalized.removeprefix("http://")

    return normalized.strip("/")


def seed_default_property(db: Session):
    property_record = (
        db.query(Property)
        .filter(Property.domain == DEFAULT_PROPERTY["domain"])
        .first()
    )

    if property_record:
        return property_record

    legacy_property = (
        db.query(Property)
        .filter(Property.domain.in_(LEGACY_DEFAULT_DOMAINS))
        .first()
    )

    if legacy_property:
        legacy_property.domain = DEFAULT_PROPERTY["domain"]

        if not legacy_property.name:
            legacy_property.name = DEFAULT_PROPERTY["name"]

        if not legacy_property.brand_name:
            legacy_property.brand_name = DEFAULT_PROPERTY["brand_name"]

        db.commit()
        db.refresh(legacy_property)

        return legacy_property

    property_record = Property(**DEFAULT_PROPERTY)
    db.add(property_record)
    db.commit()
    db.refresh(property_record)

    return property_record


def get_property(db: Session, property_id: int):
    return (
        db.query(Property)
        .filter(Property.id == property_id)
        .first()
    )


def list_properties(db: Session):
    seed_default_property(db)

    return (
        db.query(Property)
        .order_by(Property.created_at.asc())
        .all()
    )


def create_property(
    db: Session,
    name: str,
    domain: str,
    brand_name: str,
    description: str | None = None,
):
    property_record = Property(
        name=name,
        domain=normalize_property_domain(domain),
        brand_name=brand_name,
        description=description,
    )

    db.add(property_record)
    db.commit()
    db.refresh(property_record)

    return property_record


def update_property(
    db: Session,
    property_id: int,
    name: str | None = None,
    domain: str | None = None,
    brand_name: str | None = None,
    description: str | None = None,
):
    property_record = get_property(db, property_id)

    if not property_record:
        return None

    if name is not None:
        property_record.name = name

    if domain is not None:
        property_record.domain = normalize_property_domain(domain)

    if brand_name is not None:
        property_record.brand_name = brand_name

    if description is not None:
        property_record.description = description

    db.commit()
    db.refresh(property_record)

    return property_record
