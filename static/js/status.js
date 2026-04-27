function loadStatus() {
    fetch("/api/status")
        .then(r => r.json())
        .then(s => {
            document.getElementById("statusBox").innerHTML = `<p><b>Online:</b> ${s.online ? 'Yes' : 'No'}</p><p><b>Last Signal:</b> ${s.last_signal || 'N/A'}</p><p><b>Updated:</b> ${s.timestamp || 'N/A'}</p>`;
        });
}

loadStatus();
