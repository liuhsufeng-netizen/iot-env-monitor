from datetime import datetime

from app.extensions import db


class Area(db.Model):
    __tablename__ = "areas"

    area_id = db.Column(db.String(64), primary_key=True)
    area_name = db.Column(db.String(128), nullable=False)
    ac_status = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "area_id": self.area_id,
            "area_name": self.area_name,
            "ac_status": self.ac_status,
            "updated_at": self.updated_at.isoformat(),
        }
