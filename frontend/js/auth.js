const API_URL = "http://127.0.0.1:8000/api/user/login"; // Backend URL

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", login);
    }
});

async function login(event) {
    event.preventDefault();
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    
    const response = await fetch(`${API_URL}/users/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();
    
    if (response.ok) {
        localStorage.setItem("accessToken", data.access);
        localStorage.setItem("role", data.role);
        window.location.href = "dashboard.html";
    } else {
        document.getElementById("errorMessage").innerText = "Invalid username or password";
    }
}

function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("role");
    window.location.href = "login.html";
}
