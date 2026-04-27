function loadUsers() {
    fetch("/api/users")
        .then(r => r.json())
        .then(data => {
            let t = document.getElementById("userTable");
            t.innerHTML = "<tr><th>Slot</th><th>Name</th><th>Number</th><th>Access</th><th>Action</th></tr>";
            data.forEach(u => {
                t.innerHTML += 
                    <tr>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td><button onclick="delUser('')">Delete</button></td>
                    </tr>;
            });
        });
}

function addUser() {
    let payload = {
        name: document.getElementById("name").value,
        number: document.getElementById("number").value,
        start_date: document.getElementById("start_date").value,
        start_time: document.getElementById("start_time").value,
        end_date: document.getElementById("end_date").value,
        end_time: document.getElementById("end_time").value
    };

    fetch("/api/users", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify(payload)
    }).then(r => r.json()).then(x => {
        alert("SMS Sent: " + x.command);
        loadUsers();
    });
}

function delUser(number) {
    fetch("/api/users/" + number, { method:"DELETE" })
        .then(r => r.json())
        .then(x => {
            alert("Deleted: " + x.command);
            loadUsers();
        });
}

loadUsers();
