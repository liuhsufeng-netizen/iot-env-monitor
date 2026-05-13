from datetime import UTC, datetime, timedelta
from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models.ac_command_log import AcCommandLog
from app.models.alert_log import AlertLog
from app.models.area import Area
from app.models.sensor_log import SensorLog

ALLOWED_SAMPLING_INTERVALS = (10, 20, 30)
_sampling_interval_seconds = 10


def get_sampling_interval() -> dict:
    return {
        "ok": True,
        "seconds": _sampling_interval_seconds,
        "options": list(ALLOWED_SAMPLING_INTERVALS),
    }


def set_sampling_interval(seconds: int) -> tuple[dict, int]:
    if seconds not in ALLOWED_SAMPLING_INTERVALS:
        return {
            "ok": False,
            "message": f"seconds must be one of: {', '.join(str(v) for v in ALLOWED_SAMPLING_INTERVALS)}",
        }, 400

    global _sampling_interval_seconds
    _sampling_interval_seconds = seconds
    return get_sampling_interval(), 200


def ensure_default_areas() -> None:
    areas_raw = current_app.config.get("DEFAULT_AREAS", "")
    area_ids = [item.strip() for item in areas_raw.split(",") if item.strip()]

    for area_id in area_ids:
        exists = Area.query.filter_by(area_id=area_id).first()
        if exists is None:
            db.session.add(Area(area_id=area_id, area_name=area_id, ac_status=False))

    db.session.commit()


def validate_payload(payload: dict) -> tuple[bool, str]:
    required_fields = ["area_id", "temp", "humi"]
    for field in required_fields:
        if field not in payload:
            return False, f"Missing field: {field}"

    try:
        temp = float(payload["temp"])
        humi = float(payload["humi"])
    except (TypeError, ValueError):
        return False, "temp and humi must be numeric"

    if temp < -20 or temp > 80:
        return False, "temp out of range (-20 ~ 80)"
    if humi < 0 or humi > 100:
        return False, "humi out of range (0 ~ 100)"

    return True, "ok"


def process_sensor_update(payload: dict) -> tuple[dict, int]:
    is_valid, message = validate_payload(payload)
    if not is_valid:
        return {"ok": False, "message": message}, 400

    area_id = payload["area_id"]
    temp = float(payload["temp"])
    humi = float(payload["humi"])

    area = Area.query.filter_by(area_id=area_id).first()
    if area is None:
        return {"ok": False, "message": f"area_id not found: {area_id}"}, 404

    threshold = float(current_app.config.get("TEMPERATURE_THRESHOLD", 27.0))
    cooldown_seconds = int(current_app.config.get("AC_COMMAND_COOLDOWN_SECONDS", 300))

    ac_action = "NONE"
    event_id = None

    # 每次感測更新都記錄，供趨勢圖使用
    db.session.add(SensorLog(area_id=area_id, temperature=temp, humidity=humi))

    if temp > threshold:
        recent_command = (
            AcCommandLog.query.filter_by(area_id=area_id, command="ON", status="SENT")
            .order_by(AcCommandLog.sent_at.desc())
            .first()
        )

        cooldown_expired = True
        if recent_command is not None:
            # 確保 sent_at 是 UTC-aware datetime（SQLite 返回 naive datetime）
            sent_at_utc = recent_command.sent_at.replace(tzinfo=UTC) if recent_command.sent_at.tzinfo is None else recent_command.sent_at
            cooldown_until = sent_at_utc + timedelta(seconds=cooldown_seconds)
            cooldown_expired = datetime.now(UTC) >= cooldown_until

        if (not area.ac_status) and cooldown_expired:
            event_id = f"evt_{uuid4().hex[:12]}"
            db.session.add(
                AlertLog(
                    area_id=area_id,
                    event_type="TEMP_THRESHOLD_EXCEEDED",
                    threshold=threshold,
                    observed_temp=temp,
                )
            )
            db.session.add(
                AcCommandLog(
                    area_id=area_id,
                    command="ON",
                    status="SENT",
                    correlation_id=event_id,
                    response_message="Simulated AC command dispatched",
                )
            )
            area.ac_status = True
            ac_action = "ON"

    area.updated_at = datetime.utcnow()
    db.session.commit()

    return {
        "ok": True,
        "message": "accepted",
        "area_id": area_id,
        "ac_action": ac_action,
        "event_id": event_id,
    }, 202


def get_dashboard_status() -> dict:
    areas = Area.query.order_by(Area.area_id.asc()).all()
    output = []

    threshold = float(current_app.config.get("TEMPERATURE_THRESHOLD", 27.0))

    for area in areas:
        latest = (
            SensorLog.query.filter_by(area_id=area.area_id)
            .order_by(SensorLog.timestamp.desc())
            .first()
        )
        if latest is None:
            output.append(
                {
                    "area_id": area.area_id,
                    "area_name": area.area_name,
                    "temperature": None,
                    "humidity": None,
                    "last_seen": None,
                    "ac_status": area.ac_status,
                    "alarm": False,
                }
            )
            continue

        output.append(
            {
                "area_id": area.area_id,
                "area_name": area.area_name,
                "temperature": latest.temperature,
                "humidity": latest.humidity,
                "last_seen": latest.timestamp.isoformat(),
                "ac_status": area.ac_status,
                "alarm": latest.temperature > threshold,
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "areas": output,
    }


def get_area_history(area_id: str, minutes: int) -> tuple[dict, int]:
    area = Area.query.filter_by(area_id=area_id).first()
    if area is None:
        return {"ok": False, "message": f"area_id not found: {area_id}"}, 404

    since = datetime.utcnow() - timedelta(minutes=minutes)
    rows = (
        SensorLog.query.filter(SensorLog.area_id == area_id, SensorLog.timestamp >= since)
        .order_by(SensorLog.timestamp.asc())
        .all()
    )

    return {
        "ok": True,
        "area_id": area_id,
        "minutes": minutes,
        "points": [
            {
                "temperature": row.temperature,
                "humidity": row.humidity,
                # 確保 timestamp 帶有 UTC 時區信息（SQLite 返回 naive datetime）
                "timestamp": row.timestamp.replace(tzinfo=UTC).isoformat() if row.timestamp.tzinfo is None else row.timestamp.isoformat(),
            }
            for row in rows
        ],
    }, 200
