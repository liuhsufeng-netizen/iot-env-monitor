from datetime import datetime

from app.extensions import db


class AcCommandLog(db.Model):
    __tablename__ = "ac_command_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    area_id = db.Column(db.String(64), db.ForeignKey("areas.area_id"), nullable=False, index=True)
    command = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(16), nullable=False)
    correlation_id = db.Column(db.String(64), nullable=False, index=True)
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    response_message = db.Column(db.String(256), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "area_id": self.area_id,
            "command": self.command,
            "status": self.status,
            "correlation_id": self.correlation_id,
            "sent_at": self.sent_at.isoformat(),
            "response_message": self.response_message,
        }
