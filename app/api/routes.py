from datetime import UTC, datetime

from flask import Blueprint, current_app, jsonify, request

from app.extensions import socketio
from app.models.area import Area
from app.services.monitoring_service import (
    get_sampling_interval,
    get_area_history,
    get_dashboard_status,
    process_sensor_update,
    set_sampling_interval,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.post("/sensor_update")
def sensor_update():
    payload = request.get_json(silent=True) or {}
    body, status_code = process_sensor_update(payload)

    if status_code == 202:
        area_id = payload["area_id"]
        temp = float(payload["temp"])
        humi = float(payload["humi"])
        threshold = float(current_app.config.get("TEMPERATURE_THRESHOLD", 27.0))

        area = Area.query.filter_by(area_id=area_id).first()
        ac_status = area.ac_status if area else False

        socketio.emit(
            "sensor_data",
            {
                "area_id": area_id,
                "temperature": temp,
                "humidity": humi,
                "timestamp": datetime.now(UTC).isoformat(),
                "ac_status": ac_status,
                "alarm": temp > threshold,
            },
        )

    return jsonify(body), status_code


@api_bp.get("/dashboard_status")
def dashboard_status():
    return jsonify(get_dashboard_status()), 200


@api_bp.get("/areas/<string:area_id>/history")
def area_history(area_id: str):
    minutes = request.args.get("minutes", default=60, type=int)
    if minutes <= 0 or minutes > 1440:
        return jsonify({"ok": False, "message": "minutes must be between 1 and 1440"}), 400

    body, status_code = get_area_history(area_id, minutes)
    return jsonify(body), status_code


@api_bp.get("/sampling_interval")
def sampling_interval_get():
    return jsonify(get_sampling_interval()), 200


@api_bp.post("/sampling_interval")
def sampling_interval_set():
    payload = request.get_json(silent=True) or {}
    seconds = payload.get("seconds")
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "seconds must be an integer"}), 400

    body, status_code = set_sampling_interval(seconds)
    return jsonify(body), status_code
