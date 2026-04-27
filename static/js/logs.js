function loadLogs() {
    fetch("/api/logs")
        .then(r => r.json())
        .then(data => {
            let t = document.getElementById("logTable");
            t.innerHTML = "<tr><th>Time</th><th>Sender</th><th>Message</th></tr>";
            data.forEach(l => {
                t.innerHTML += `<tr><td>${l.timestamp}</td><td>${l.sender}</td><td>${l.message}</td></tr>`;
            });
        });
}

loadLogs();
