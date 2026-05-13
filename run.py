from app import create_app
from app.extensions import db, socketio
from app.services.monitoring_service import ensure_default_areas

app = create_app()

with app.app_context():
    db.create_all()
    ensure_default_areas()

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("IoT Environment Monitor starting")
    print("=" * 50)
    print("URL: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        use_reloader=False,
        use_debugger=False,
        allow_unsafe_werkzeug=True,
    )
