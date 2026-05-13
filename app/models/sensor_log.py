from datetime import datetime

from app.extensions import db


class SensorLog(db.Model):
    __tablename__ = "sensor_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    area_id = db.Column(db.String(64), db.ForeignKey("areas.area_id"), nullable=False, index=True)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "area_id": self.area_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "timestamp": self.timestamp.isoformat(),
        }
