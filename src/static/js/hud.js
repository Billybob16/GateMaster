function setLoading(active) {
    const overlay = document.getElementById("hud-loading-overlay");
    if (!overlay) return;
    overlay.classList.toggle("active", !!active);
}

function initSidebarToggle() {
    const sidebar = document.getElementById("hud-sidebar");
    const toggle = document.getElementById("hud-sidebar-toggle");
    if (!sidebar || !toggle) return;

    toggle.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
    });
}

function initThemeToggle() {
    const btn = document.getElementById("hud-theme-toggle");
    if (!btn) return;

    btn.addEventListener("click", () => {
        const body = document.body;
        if (body.classList.contains("hud-theme-dark")) {
            body.classList.remove("hud-theme-dark");
            body.classList.add("hud-theme-alt");
        } else {
            body.classList.remove("hud-theme-alt");
            body.classList.add("hud-theme-dark");
        }
    });
}

async function updateTopbarSignal() {
    const el = document.getElementById("topbar-signal");
    if (!el) return;

    try {
        const res = await fetch("/api/signal-data");
        const data = await res.json();
        const last = data[data.length - 1]?.value ?? "–";
        el.textContent = last;
    } catch {
        el.textContent = "–";
    }
}

window.addEventListener("DOMContentLoaded", () => {
    initSidebarToggle();
    initThemeToggle();
    updateTopbarSignal();
});
