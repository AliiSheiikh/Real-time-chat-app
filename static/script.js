const messages = document.getElementById("messages");
const form = document.getElementById("form");
const input = document.getElementById("input");

const ws = new WebSocket(`ws://${window.location.host}/ws`);

ws.onmessage = (event) => {
    const li = document.createElement("li");
    li.textContent = event.data;
    messages.appendChild(li);
    messages.scrollTop = messages.scrollHeight;
};

form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (input.value === "") return;
    ws.send(input.value);
    input.value = "";
});
