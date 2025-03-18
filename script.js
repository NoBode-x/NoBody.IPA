let apps = [
{ name: "تطبيق الطقس", description: "تعرف على حالة الطقس بسهولة", image: "https://via.placeholder.com/80", link: "#", date: "2024-02-01" },
{ name: "مدير المهام", description: "إدارة مهامك اليومية بكفاءة", image: "https://via.placeholder.com/80", link: "#", date: "2024-01-15" },
{ name: "محرر الصور", description: "عدل صورك بسهولة وسرعة", image: "https://via.placeholder.com/80", link: "#", date: "2024-01-30" }
];

function loadApps() {
const appList = document.getElementById("apps-list");
if (!appList) return;
appList.innerHTML = "";
apps.forEach(app => {
const appElement = document.createElement("div");
appElement.classList.add("app");
appElement.innerHTML = `
<img src="${app.image}" alt="${app.name}">
<div class="app-info">
<h3>${app.name}</h3>
<p>${app.description}</p>
</div>
<a href="${app.link}"><button class="download-btn">تحميل</button></a>
`;
appList.appendChild(appElement);
});
}

function sortApps() {
const sortBy = document.getElementById("sort").value;
if (sortBy === "name") {
apps.sort((a, b) => a.name.localeCompare(b.name));
} else if (sortBy === "latest") {
apps.sort((a, b) => new Date(b.date) - new Date(a.date));
}
loadApps();
}

function loadAdminApps() {
const adminList = document.getElementById("admin-apps-list");
if (!adminList) return;
adminList.innerHTML = "";
apps.forEach((app, index) => {
const appElement = document.createElement("div");
appElement.classList.add("app");
appElement.innerHTML = `
<img src="${app.image}" alt="${app.name}">
<div class="app-info">
<h3>${app.name}</h3>
<p>${app.description}</p>
</div>
<button onclick="deleteApp(${index})">حذف</button>
`;
adminList.appendChild(appElement);
});
}

function deleteApp(index) {
apps.splice(index, 1);
loadAdminApps();
}

function addDummyApp() {
apps.push({ name: "تطبيق جديد", description: "تطبيق تمت إضافته", image: "https://via.placeholder.com/80", link: "#", date: new Date().toISOString().split('T')[0] });
loadAdminApps();
}

// ✅ نظام تسجيل الدخول والخروج
const adminUser = { username: "admin", password: "1234" };

function login() {
const username = document.getElementById("username").value;
const password = document.getElementById("password").value;
const errorMessage = document.getElementById("error-message");

if (username === adminUser.username && password === adminUser.password) {
localStorage.setItem("isLoggedIn", "true");
window.location.href = "admin.html";
} else {
errorMessage.textContent = "اسم المستخدم أو كلمة المرور غير صحيحة!";
}
}

function checkLogin() {
if (localStorage.getItem("isLoggedIn") !== "true") {
window.location.href = "login.html";
}
}

function logout() {
localStorage.removeItem("isLoggedIn");
window.location.href = "login.html";
}

window.onload = function() {
loadApps();
loadAdminApps();
};
