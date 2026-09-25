from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - registers all SQLAlchemy mappings
from app.core.database import Base
from app.models.property import Property
from app.models.website_audit import WebsiteAudit
from app.services.website_audit.repository import get_audit, get_latest_audit


def test_new_audit_has_distinct_id_and_exact_handoff_does_not_reuse_history():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    try:
        property_record = Property(
            name="GeoAIResume",
            domain="https://geoairesume-web-six.vercel.app",
        )
        session.add(property_record)
        session.commit()

        previous = WebsiteAudit(
            property_id=property_record.id,
            base_url="https://geoairesume-web-six.vercel.app/",
            status="completed",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        session.add(previous)
        session.commit()

        current = WebsiteAudit(
            property_id=property_record.id,
            base_url="https://geoairesume-web-six.vercel.app/",
            status="completed",
            created_at=datetime.now(timezone.utc),
        )
        session.add(current)
        session.commit()

        assert current.id != previous.id
        assert get_latest_audit(session, property_record.id).id == current.id
        assert get_audit(session, property_record.id, current.id).id == current.id
        assert get_audit(session, property_record.id + 1, current.id) is None
    finally:
        session.close()
        engine.dispose()
