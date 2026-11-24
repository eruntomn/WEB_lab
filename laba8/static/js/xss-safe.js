document.getElementById("show-btn").addEventListener("click", async () => {
  const id = document.getElementById("user-id").value;
  const response = await fetch(`/api/users/${id}/profile`, { credentials: "same-origin" });
  const profile = await response.json();
  document.getElementById("profile").textContent = profile.name + ": " + profile.bio;
});