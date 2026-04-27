function sendCmd() {
    let cmd = document.getElementById("cmd").value;

    fetch("/api/send", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify({ cmd: cmd })
    })
    .then(r => r.json())
    .then(x => {
        document.getElementById("resp").innerHTML += <p>Sent: </p>;
    });
}
