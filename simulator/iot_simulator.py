import random
import time
from datetime import UTC, datetime

import requests

BASE_URL = "http://127.0.0.1:5000/api/sensor_update"
HEALTH_URL = "http://127.0.0.1:5000/api/dashboard_status"
SAMPLING_INTERVAL_URL = "http://127.0.0.1:5000/api/sampling_interval"
AREAS = ["Zone_A", "Zone_B", "Zone_C", "Zone_D"]

DEFAULT_SEND_INTERVAL = 10
RETRY_INTERVAL = 3
RETRY_MAX = 3
WAIT_POLL = 3


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def wait_for_server(label: str = "等待伺服器啟動") -> None:
    attempt = 0
    while True:
        try:
            requests.get(HEALTH_URL, timeout=2)
            print(f"[{_now()}] 伺服器已就緒")
            return
        except requests.RequestException:
            attempt += 1
            print(f"[{_now()}] {label}... (第 {attempt} 次，{WAIT_POLL}s 後重試)")
            time.sleep(WAIT_POLL)


def get_send_interval() -> int:
    try:
        res = requests.get(SAMPLING_INTERVAL_URL, timeout=3)
        data = res.json()
        seconds = int(data.get("seconds", DEFAULT_SEND_INTERVAL))
        if seconds not in (10, 20, 30):
            return DEFAULT_SEND_INTERVAL
        return seconds
    except (requests.RequestException, ValueError, TypeError):
        return DEFAULT_SEND_INTERVAL


def send_one(area: str) -> bool:
    payload = {
        "area_id": area,
        "temp": round(random.uniform(24.0, 30.0), 2),
        "humi": random.randint(40, 70),
        "device_time": datetime.now(UTC).isoformat(),
    }

    for attempt in range(1, RETRY_MAX + 1):
        try:
            res = requests.post(BASE_URL, json=payload, timeout=5)
            print(
                f"[{_now()}] {area} temp={payload['temp']}°C humi={payload['humi']}% -> HTTP {res.status_code}"
            )
            return True
        except requests.RequestException as exc:
            if attempt < RETRY_MAX:
                print(f"[{_now()}] {area} 發送失敗，{RETRY_INTERVAL}s 後重試：{exc}")
                time.sleep(RETRY_INTERVAL)
            else:
                print(f"[{_now()}] {area} 連續失敗，略過本次：{exc}")
    return False


def send_once() -> int:
    failures = 0
    for area in AREAS:
        if not send_one(area):
            failures += 1
    return failures


def main() -> None:
    print(f"IoT Simulator 啟動，區域：{', '.join(AREAS)}")
    wait_for_server()

    while True:
        failures = send_once()

        if failures == len(AREAS):
            print(f"[{_now()}] 全部區域都失敗，等待伺服器恢復")
            wait_for_server(label="等待伺服器恢復")
            print(f"[{_now()}] 伺服器恢復，繼續發送")

        interval = get_send_interval()
        print(f"[{_now()}] 下次發送間隔：{interval} 秒")
        time.sleep(interval)


if __name__ == "__main__":
    main()
