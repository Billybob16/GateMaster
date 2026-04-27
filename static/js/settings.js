function loadCfg() {
    fetch("/api/config")
        .then(r => r.json())
        .then(cfg => {
            document.getElementById("cfg").value = JSON.stringify(cfg, null, 4);
        });
}

function saveCfg() {
    let cfg = document.getElementById("cfg").value;
    fetch("/api/config", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:cfg
    }).then(() => alert("Saved"));
}

loadCfg();
