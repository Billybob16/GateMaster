// Fetch devices
async function loadDevices() {
    const res = await fetch("/api/devices");
    const data = await res.json();

    const tbody = document.querySelector("#device-table tbody");
    if (!tbody) return;

    tbody.innerHTML = "";

    data.forEach(d => {
        const row = `
            <tr>
                <td>${d.name}</td>
                <td>${d.site}</td>
                <td>${d.status}</td>
                <td>${d.signal}%</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

// Fetch history
async function loadHistory() {
    const res = await fetch("/api/history");
    const data = await res.json();

    const tbody = document.querySelector("#history-table tbody");
    if (!tbody) return;

    tbody.innerHTML = "";

    data.forEach(h => {
        const row = `
            <tr>
                <td>${h.time}</td>
                <td>${h.device}</td>
                <td>${h.event}</td>
                <td>${h.signal}%</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

// Fetch settings
async function loadSettings() {
    const el = document.querySelector("#settings-json");
    if (!el) return;

    const res = await fetch("/api/settings");
    const data = await res.json();
    el.textContent = JSON.stringify(data, null, 2);
}

// Fetch system info
async function loadSystem() {
    const el = document.querySelector("#system-json");
    if (!el) return;

    const res = await fetch("/api/system");
    const data = await res.json();
    el.textContent = JSON.stringify(data, null, 2);
}

// Signal graph
let chart;
async function loadSignalGraph() {
    const canvas = document.getElementById("signalChart");
    if (!canvas) return;

    const res = await fetch("/api/signal");
    const data = await res.json();

    const labels = data.map(p => p.time);
    const values = data.map(p => p.value);

    if (!chart) {
        chart = new Chart(canvas, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Average Signal",
                    data: values,
                    borderColor: "#00ff88",
                    backgroundColor: "rgba(0,255,136,0.2)",
                    tension: 0.2
                }]
            },
            options: {
                scales: {
                    x: { ticks: { color: "#00ff88" } },
                    y: { ticks: { color: "#00ff88" } }
                }
            }
        });
    } else {
        chart.data.labels = labels;
        chart.data.datasets[0].data = values;
        chart.update();
    }
}

// Auto-refresh
setInterval(() => {
    loadDevices();
    loadHistory();
    loadSettings();
    loadSystem();
    loadSignalGraph();
}, 3000);

// Initial load
loadDevices();
loadHistory();
loadSettings();
loadSystem();
loadSignalGraph();
