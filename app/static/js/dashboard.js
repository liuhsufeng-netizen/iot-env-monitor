const cardsEl = document.getElementById("areaCards");
const generatedAtEl = document.getElementById("generatedAt");
const areaSelectEl = document.getElementById("areaSelect");
const intervalSelectEl = document.getElementById("intervalSelect");
const chartCtx = document.getElementById("trendChart");

const areaCache = {};
const historyCache = {};

let selectedArea = null;
let trendChart = null;
let socket = null;

const MAX_CHART_POINTS = 120; // fallback cap
const CHART_WINDOW_MS = 300 * 1000; // fixed 300-second window
const X_TICK_STEP_MS = 5 * 1000; // 5-second tick step

function fmtValue(value, suffix) {
  if (value === null || value === undefined) return "--";
  return `${value}${suffix}`;
}

function fmtTime(isoStr) {
  if (!isoStr) return "--";
  return new Date(isoStr).toLocaleString("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function toEpochMs(isoStr) {
  return new Date(isoStr).getTime();
}

function keepLatestPoints(points) {
  if (points.length <= MAX_CHART_POINTS) return points;
  return points.slice(-MAX_CHART_POINTS);
}

function buildSeriesWithLeftGap(points, xMin) {
  const visible = points.filter((p) => p.x >= xMin);
  return [{ x: xMin, y: null }, ...visible];
}

function upsertHistoryPoint(areaId, point) {
  const list = historyCache[areaId] || [];
  const last = list[list.length - 1];
  if (!last || last.timestamp !== point.timestamp) {
    list.push(point);
  } else {
    list[list.length - 1] = point;
  }
  historyCache[areaId] = keepLatestPoints(list);
}

function buildCardHtml(area) {
  const alarmText = area.alarm ? `<p class="alarm-text">超過警示溫度</p>` : "";
  return `
    <h3>${area.area_name || area.area_id}</h3>
    <p>溫度: ${fmtValue(area.temperature, "°C")}</p>
    <p>濕度: ${fmtValue(area.humidity, "%")}</p>
    ${alarmText}
    <span class="badge ${area.ac_status ? "on" : "off"}">${area.ac_status ? "AC ON" : "AC OFF"}</span>
    <div class="meta">最後更新: ${fmtTime(area.last_seen)}</div>
  `;
}

function renderCards(areas) {
  cardsEl.innerHTML = "";
  areas.forEach((area) => {
    areaCache[area.area_id] = area;
    const div = document.createElement("div");
    div.className = `card ${area.alarm ? "alarm" : ""}`;
    div.id = `card-${area.area_id}`;
    div.innerHTML = buildCardHtml(area);
    cardsEl.appendChild(div);
  });
}

function updateCard(data) {
  const prev = areaCache[data.area_id] || {};
  const area = {
    area_id: data.area_id,
    area_name: prev.area_name || data.area_id,
    temperature: data.temperature,
    humidity: data.humidity,
    ac_status: data.ac_status,
    alarm: data.alarm,
    last_seen: data.timestamp,
  };

  areaCache[data.area_id] = area;
  const card = document.getElementById(`card-${data.area_id}`);
  if (!card) return;

  card.className = `card ${area.alarm ? "alarm" : ""}`;
  card.innerHTML = buildCardHtml(area);
}

function renderAreaSelect(areas) {
  const previous = selectedArea;
  areaSelectEl.innerHTML = "";

  areas.forEach((area) => {
    const option = document.createElement("option");
    option.value = area.area_id;
    option.textContent = area.area_name || area.area_id;
    areaSelectEl.appendChild(option);
  });

  if (previous && areas.some((a) => a.area_id === previous)) {
    selectedArea = previous;
  } else if (areas.length > 0) {
    selectedArea = areas[0].area_id;
  }

  areaSelectEl.value = selectedArea || "";
}

function createChart(tempPoints, humiPoints) {
  if (trendChart) trendChart.destroy();

  const nowMs = Date.now();
  const xMin = nowMs - CHART_WINDOW_MS;
  const xMax = nowMs;
  const tempSeries = buildSeriesWithLeftGap(tempPoints, xMin);
  const humiSeries = buildSeriesWithLeftGap(humiPoints, xMin);

  trendChart = new Chart(chartCtx, {
    type: "line",
    data: {
      datasets: [
        {
          label: "Temperature (°C)",
          data: tempSeries,
          borderColor: "#dc4f4f",
          backgroundColor: "rgba(220,79,79,0.1)",
          yAxisID: "y",
          tension: 0,
          spanGaps: false,
          pointRadius: 1,
          pointBackgroundColor: "#dc4f4f",
          fill: false,
          borderWidth: 2,
        },
        {
          label: "Humidity (%)",
          data: humiSeries,
          borderColor: "#1769aa",
          backgroundColor: "rgba(23,105,170,0.1)",
          yAxisID: "y1",
          tension: 0,
          spanGaps: false,
          pointRadius: 1,
          pointBackgroundColor: "#1769aa",
          fill: false,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      parsing: false,
      animation: { duration: 0 },
      scales: {
        x: {
          type: "linear",
          min: xMin,
          max: xMax,
          title: { display: true, text: "Time" },
          ticks: {
            stepSize: X_TICK_STEP_MS,
            autoSkip: false,
            callback(value, index) {
              if (index % 6 !== 0) return "";
              return new Date(value).toLocaleTimeString("zh-TW", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              });
            },
          },
        },
        y: {
          type: "linear",
          position: "left",
          title: { display: true, text: "Temperature (°C)" },
          min: 20,
          max: 35,
        },
        y1: {
          type: "linear",
          position: "right",
          grid: { drawOnChartArea: false },
          title: { display: true, text: "Humidity (%)" },
          min: 30,
          max: 80,
        },
      },
    },
  });
}

function pushChartPoint(timestamp, temperature, humidity) {
  if (!trendChart) return;

  const x = toEpochMs(timestamp);
  const xMin = x - CHART_WINDOW_MS;
  const xMax = x;

  const currentTemp = trendChart.data.datasets[0].data
    .filter((p) => p && p.y !== null)
    .concat({ x, y: temperature });
  const currentHumi = trendChart.data.datasets[1].data
    .filter((p) => p && p.y !== null)
    .concat({ x, y: humidity });

  const trimmedTemp = keepLatestPoints(currentTemp).filter((p) => p.x >= xMin);
  const trimmedHumi = keepLatestPoints(currentHumi).filter((p) => p.x >= xMin);

  trendChart.data.datasets[0].data = buildSeriesWithLeftGap(trimmedTemp, xMin);
  trendChart.data.datasets[1].data = buildSeriesWithLeftGap(trimmedHumi, xMin);
  trendChart.options.scales.x.min = xMin;
  trendChart.options.scales.x.max = xMax;
  trendChart.update("none");
}

async function loadHistory() {
  if (!selectedArea) return;

  if (historyCache[selectedArea] && historyCache[selectedArea].length > 0) {
    const points = historyCache[selectedArea];
    const tempPoints = points.map((p) => ({ x: toEpochMs(p.timestamp), y: p.temperature }));
    const humiPoints = points.map((p) => ({ x: toEpochMs(p.timestamp), y: p.humidity }));
    createChart(tempPoints, humiPoints);
    return;
  }

  try {
    const res = await fetch(`/api/areas/${selectedArea}/history?minutes=120`);
    const data = await res.json();
    const points = data.ok && data.points ? keepLatestPoints(data.points) : [];
    historyCache[selectedArea] = points;

    const tempPoints = points.map((p) => ({ x: toEpochMs(p.timestamp), y: p.temperature }));
    const humiPoints = points.map((p) => ({ x: toEpochMs(p.timestamp), y: p.humidity }));

    createChart(tempPoints, humiPoints);
  } catch (error) {
    console.error("[Chart] load history failed:", error);
    createChart([], []);
  }
}

async function loadStatus() {
  const res = await fetch("/api/dashboard_status");
  const data = await res.json();

  generatedAtEl.textContent = `最後更新：${new Date(data.generated_at).toLocaleString("zh-TW")}`;
  renderCards(data.areas);
  renderAreaSelect(data.areas);
  await loadHistory();
}

async function loadSamplingInterval() {
  try {
    const res = await fetch("/api/sampling_interval");
    const data = await res.json();
    if (!data.ok) return;
    intervalSelectEl.value = String(data.seconds);
  } catch (error) {
    console.error("[Interval] load failed:", error);
  }
}

async function setSamplingInterval(seconds) {
  try {
    const res = await fetch("/api/sampling_interval", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seconds }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.message || "set interval failed");
    }
    intervalSelectEl.value = String(data.seconds);
    return true;
  } catch (error) {
    console.error("[Interval] update failed:", error);
    return false;
  }
}

function initSocketIO() {
  socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5,
  });

  socket.on("sensor_data", (data) => {
    generatedAtEl.textContent = `最後更新：${new Date(data.timestamp).toLocaleString("zh-TW")}`;
    updateCard(data);
    upsertHistoryPoint(data.area_id, {
      timestamp: data.timestamp,
      temperature: data.temperature,
      humidity: data.humidity,
    });

    if (data.area_id === selectedArea) {
      pushChartPoint(data.timestamp, data.temperature, data.humidity);
    }
  });
}

areaSelectEl.addEventListener("change", async (e) => {
  selectedArea = e.target.value;
  await loadHistory();
});

intervalSelectEl.addEventListener("change", async (e) => {
  const seconds = Number(e.target.value);
  const ok = await setSamplingInterval(seconds);
  if (!ok) {
    await loadSamplingInterval();
  }
});

Promise.all([loadStatus(), loadSamplingInterval()]).then(() => {
  initSocketIO();
});
