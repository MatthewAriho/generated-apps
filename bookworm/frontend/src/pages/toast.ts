export function showToast(message: string, type: "success" | "error" | "info" = "info"): void {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideOut 0.25s ease forwards";
    setTimeout(() => toast.remove(), 260);
  }, 3500);
}
