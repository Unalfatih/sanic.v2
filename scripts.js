const API_URL = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("register-button").onclick = registerUser;
  document.getElementById("login-button").onclick = loginUser;
  document.getElementById("fetch-users-button").onclick = fetchUsers;
  document.getElementById("fetch-events-button").onclick = fetchEvents;
  document.getElementById("fetch-announcements-button").onclick = fetchAnnouncements;
  document.getElementById("logout-button").onclick = logoutUser;
  document.getElementById("update-user-button").onclick = updateUser;
  document.getElementById("delete-event-button").onclick = deleteEvent;
});


// Kullanıcı kaydı
async function registerUser() {
  const firstName = document.getElementById("register-firstname").value;
  const lastName = document.getElementById("register-lastname").value;
  const email = document.getElementById("register-email").value;
  const password = document.getElementById("register-password").value;
  const role = document.getElementById("register-role").value;
  const isActive = document.getElementById("register-active").checked;

  const response = await fetch(`${API_URL}/users/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      first_name: firstName,
      last_name: lastName,
      email,
      password,
      role,
      is_active: isActive,
    }),
  });

  const result = await response.json();
  alert(result.message);
}


// Kullanıcı girişi
async function loginUser() {
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;

  if (!email || !password) {
    alert("Email and password are required!");
    return;
  }

  const response = await fetch(`${API_URL}/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const result = await response.json();

  if (response.status === 200) {
    alert("Login successful!");
    window.location.href = "form.html"; // Giriş başarılıysa başka bir sayfaya yönlendirilir
  } else {
    alert(result.message);
  }
}

async function fetchUsers() {
  try {
    const response = await fetch(`${API_URL}/users/getall`);
    const data = await response.json();

    // API'den dönen veriden "users" anahtarını çekiyoruz
    const users = data.users;

    const userList = document.getElementById("user-list");
    userList.innerHTML = "";

    users.forEach((user) => {
      const li = document.createElement("li");
      li.textContent = `${user.first_name} ${user.last_name} (${user.email}) - Role: ${user.role} - Created At: ${user.created_at}`;
      userList.appendChild(li);
    });
  } catch (error) {
    console.error("Kullanıcılar alınırken bir hata oluştu:", error);
    alert("Kullanıcı verisi alınırken bir hata oluştu. Lütfen konsolu kontrol edin.");
  }
}


// Etkinlikleri getir
async function fetchEvents() {
  const response = await fetch(`${API_URL}/events/getall`);
  const data = await response.json();
  const events = data.events;

  const eventList = document.getElementById("event-list");
  eventList.innerHTML = "";

  events.forEach((event) => {
    const li = document.createElement("li");
    li.textContent = `${event.title} - ${event.description} (Starts: ${event.start_date}, Ends: ${event.end_date})`;
    eventList.appendChild(li);
  });
}

// Duyuruları getir
async function fetchAnnouncements() {
  const response = await fetch(`${API_URL}/announcements/getall`);
  const data = await response.json();
  const announcements = data.announcements;

  const announcementList = document.getElementById("announcement-list");
  announcementList.innerHTML = "";

  announcements.forEach((announcement) => {
    const li = document.createElement("li");
    li.textContent = `${announcement.title} - ${announcement.content} (Created At: ${announcement.created_at})`;
    announcementList.appendChild(li);
  });
}

async function createNewEvent() {
  const title = document.getElementById("event-title").value;
  const description = document.getElementById("event-description").value;
  const startDate = document.getElementById("event-start-date").value;
  const endDate = document.getElementById("event-end-date").value;
  const createdBy = document.getElementById("event-created-by").value;

  const response = await fetch(`${API_URL}/events/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      description,
      start_date: startDate,
      end_date: endDate,
      created_by: createdBy,
    }),
  });

  const result = await response.json();
  alert(result.message);
}


async function createAnnouncement() {
  const title = document.getElementById("announcement-title").value;
  const content = document.getElementById("announcement-content").value;
  const createdBy = document.getElementById("announcement-created-by").value; // Kullanıcı ID'si

  const response = await fetch(`${API_URL}/announcements/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      content,
      created_by: createdBy,
    }),
  });

  const result = await response.json();
  alert(result.message);
}


// Kullanıcı çıkışı
function logoutUser() {
  alert("You have been logged out!");
  window.location.href = "index.html";
}


// Kullanıcı güncelleme
async function updateUser() {
  const userId = document.getElementById("update-user-id").value;
  const firstName = document.getElementById("update-firstname").value;
  const lastName = document.getElementById("update-lastname").value;
  const email = document.getElementById("update-email").value;
  const newPassword = document.getElementById("update-password").value;
  const currentPassword = document.getElementById("update-current-password").value;
  const isActive = document.getElementById("update-active").checked;

  const payload = {};
  if (firstName) payload.first_name = firstName;
  if (lastName) payload.last_name = lastName;
  if (email) payload.email = email;
  if (newPassword) {
    payload.new_password = newPassword;
    payload.current_password = currentPassword;
  }
  payload.is_active = isActive;

  const response = await fetch(`${API_URL}/users/update/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const result = await response.json();
  alert(result.message);
}

// Etkinlik silme
async function deleteEvent() {
  const eventId = document.getElementById("delete-event-id").value;

  const response = await fetch(`${API_URL}/events/delete/${eventId}`, {
    method: "DELETE",
  });

  const result = await response.json();
  alert(result.message);
}