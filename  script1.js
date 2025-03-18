let apps = [
{ name: "تطبيق الطقس", description: "تعرف على حالة الطقس بسهولة", image: "https://via.placeholder.com/80", link: "#", date: "2024-02-01", rating: 0, comments: [] },
{ name: "مدير المهام", description: "إدارة مهامك اليومية بكفاءة", image: "https://via.placeholder.com/80", link: "#", date: "2024-01-15", rating: 0, comments: [] },
{ name: "محرر الصور", description: "عدل صورك بسهولة وسرعة", image: "https://via.placeholder.com/80", link: "#", date: "2024-01-30", rating: 0, comments: [] }
];

function loadApps() {
const appList = document.getElementById("apps-list");
appList.innerHTML = "";

apps.forEach((app, index) => {
const appElement = document.createElement("div");
appElement.classList.add("app");
appElement.innerHTML = `
<img src="${app.image}" alt="${app.name}">
<div class="app-info">
<h3>${app.name}</h3>
<p>${app.description}</p>
</div>
<a href="${app.link}"><button class="download-btn">تحميل</button></a>

<div class="rating-container">
<span>التقييم:</span>
${[1, 2, 3, 4, 5].map(num => `
<span class="star" onclick="rateApp(${index}, ${num})">&#9733;</span>
`).join('')}
<span id="rating-${index}">${app.rating} نجوم</span>
</div>

<div class="comments-container">
<h4>التعليقات:</h4>
<div id="comments-${index}">
${app.comments.map(comment => `<p>${comment}</p>`).join('')}
</div>
<input type="text" class="comment-input" id="comment-input-${index}" placeholder="أضف تعليقك">
<button class="comment-btn" onclick="addComment(${index})">إضافة</button>
</div>
`;
appList.appendChild(appElement);
});

updateRatings();
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

function rateApp(index, rating) {
apps[index].rating = rating;
updateRatings();
}

function updateRatings() {
apps.forEach((app, index) => {
document.getElementById(`rating-${index}`).innerText = `${app.rating} نجوم`;
document.querySelectorAll(`.rating-container:nth-child(${index + 1}) .star`).forEach((star, starIndex) => {
star.classList.toggle("selected", starIndex < app.rating);
});
});
}

function addComment(index) {
const input = document.getElementById(`comment-input-${index}`);
const commentText = input.value.trim();
if (commentText) {
apps[index].comments.push(commentText);
input.value = "";
loadApps();
}
}

window.onload = loadApps;
