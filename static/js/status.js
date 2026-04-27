function loadStatus() {
    fetch("/api/status")
        .then(r => r.json())
        .then(s => {
            document.getElementById("statusBox").innerHTML = 
                <p><b>Online:</b> </p>
                <p><b>Last Signal:</b> </p>
                <p><b>Updated:</b> </p>
            ;
        });
}

loadStatus();
