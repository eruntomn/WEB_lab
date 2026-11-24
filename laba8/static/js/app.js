const state = { csrf: null, userId: null };
const $ = (id) => document.getElementById(id);

function out(data) {
  $("output").textContent = JSON.stringify(data, null, 2);
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.csrf) headers["X-CSRF-Token"] = state.csrf;
  const response = await fetch("/api" + path, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  const text = await response.text();
  return { status: response.status, body: text ? JSON.parse(text) : null };
}

function showUser(user) {
  state.csrf = user.csrf_token;
  state.userId = user.id;
  $("user-name").textContent = user.name; // textContent: безопасный вывод
  $("user-role").textContent = user.role;
  $("login-box").hidden = true;
  $("profile-box").hidden = false;
}

async function loadProfile() {
  const { body } = await api(`/users/${state.userId}/profile`);
  $("bio").value = body.bio || "";
  $("city").value = body.city || "";
}

async function restoreSession() {
  const { status, body } = await api("/me");
  if (status === 200) {
    showUser(body);
    await loadProfile();
  }
}

$("login-btn").addEventListener("click", async () => {
  const payload = { email: $("email").value, password: $("password").value };
  const { status, body } = await api("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (status === 200) {
    const { csrf_token, ...safe } = body;
    out({ status, body: safe });
    showUser(body);
    await loadProfile();
  } else {
    out({ status, body });
  }
});

$("save-btn").addEventListener("click", async () => {
  const payload = { bio: $("bio").value, city: $("city").value };
  const { status, body } = await api(`/users/${state.userId}/profile`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  out({ status, body });
});

$("logout-btn").addEventListener("click", async () => {
  await api("/auth/logout", { method: "POST" });
  state.csrf = null;
  location.reload();
});

restoreSession();