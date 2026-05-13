from datetime import datetime

from app.extensions import db


class AlertLog(db.Model):
    __tablename__ = "alert_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    area_id = db.Column(db.String(64), db.ForeignKey("areas.area_id"), nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False)
    threshold = db.Column(db.Float, nullable=False)
    observed_temp = db.Column(db.Float, nullable=False)
    triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "area_id": self.area_id,
            "event_type": self.event_type,
            "threshold": self.threshold,
            "observed_temp": self.observed_temp,
            "triggered_at": self.triggered_at.isoformat(),
        }
