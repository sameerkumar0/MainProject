const API_URL = "http://127.0.0.1:8000/api"; // Backend URL

document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.includes("dashboard.html")) {
        loadTasks();
    }
});

async function loadTasks() {
    const accessToken = localStorage.getItem("accessToken");
    const response = await fetch(`${API_URL}/tasks/`, {
        headers: { "Authorization": `Bearer ${accessToken}` }
    });

    const tasks = await response.json();
    displayTasks(tasks);
}

function displayTasks(tasks) {
    const taskList = document.getElementById("taskList");
    taskList.innerHTML = "";

    tasks.forEach(task => {
        const taskItem = document.createElement("div");
        taskItem.innerHTML = `
            <h3>${task.title}</h3>
            <p>${task.description}</p>
            <p>Status: <b>${task.status}</b></p>
            ${localStorage.getItem("role") === "employee" ? `<button onclick="updateTask(${task.id})">Mark Complete</button>` : ""}
        `;
        taskList.appendChild(taskItem);
    });
}

async function updateTask(taskId) {
    const accessToken = localStorage.getItem("accessToken");

    await fetch(`${API_URL}/tasks/${taskId}/`, {
        method: "PATCH",
        headers: {
            "Authorization": `Bearer ${accessToken}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ status: "completed" })
    });

    loadTasks(); // Refresh task list
}
