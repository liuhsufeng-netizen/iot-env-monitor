# IoT 溫溼度監控與空調聯動系統

使用 Flask + SQLite 實作的監控後端，提供感測資料接收、儀表板狀態查詢、歷史曲線資料。

## 快速啟動

1. 建立虛擬環境並安裝依賴

   Windows PowerShell:

   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   pip install -r requirements.txt

2. 啟動伺服器

   python run.py

3. 開啟儀表板

   http://127.0.0.1:5000/

4. 啟動模擬器（另一個終端）

   python simulator/iot_simulator.py

## API

- POST /api/sensor_update
- GET /api/dashboard_status
- GET /api/areas/{area_id}/history?minutes=60

## 預設區域

可透過環境變數 DEFAULT_AREAS 設定，預設值如下：

Zone_A,Zone_B,Zone_C
