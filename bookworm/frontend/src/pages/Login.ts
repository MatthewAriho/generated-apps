import { auth, ApiError } from "../api";
import { navigate } from "../router";
import { isAuthenticated } from "../auth";

export function renderLogin(): string {
  if (isAuthenticated()) {
    setTimeout(() => navigate("/library"), 0);
    return `<div class="auth-page"><div class="spinner"></div></div>`;
  }

  return `
    <div class="auth-page">
      <div class="auth-card">
        <div class="auth-logo">📚 Bookworm</div>
        <div class="auth-tagline">Your personal library, everywhere</div>

        <div id="auth-error" class="form-error" style="display:none"></div>

        <form id="login-form" class="auth-form">
          <div class="input-group">
            <label class="input-label" for="username">Username</label>
            <input id="username" class="input" type="text" autocomplete="username" placeholder="your-username" required />
          </div>
          <div class="input-group">
            <label class="input-label" for="password">Password</label>
            <input id="password" class="input" type="password" autocomplete="current-password" placeholder="••••••••" required />
          </div>
          <button type="submit" class="btn btn-primary" id="submit-btn">Sign in</button>
        </form>

        <div class="auth-switch">
          <span id="switch-text">Don't have an account?</span>
          <button id="toggle-mode">Register</button>
        </div>
      </div>
    </div>
  `;
}

document.addEventListener("page:mounted", (e: Event) => {
  const route = (e as CustomEvent).detail;
  if (route?.name !== "login") return;
  bootLoginPage();
});

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("login-form")) bootLoginPage();
});

function bootLoginPage(): void {
  const form = document.getElementById("login-form") as HTMLFormElement | null;
  if (!form) return;

  let isRegister = false;

  const toggleBtn = document.getElementById("toggle-mode")!;
  const switchText = document.getElementById("switch-text")!;
  const submitBtn = document.getElementById("submit-btn") as HTMLButtonElement;
  const errorEl = document.getElementById("auth-error") as HTMLElement;
  const passwordInput = document.getElementById("password") as HTMLInputElement;

  toggleBtn.addEventListener("click", () => {
    isRegister = !isRegister;
    submitBtn.textContent = isRegister ? "Create account" : "Sign in";
    toggleBtn.textContent = isRegister ? "Login" : "Register";
    switchText.textContent = isRegister ? "Already have an account?" : "Don't have an account?";
    passwordInput.autocomplete = isRegister ? "new-password" : "current-password";
    errorEl.style.display = "none";
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = (document.getElementById("username") as HTMLInputElement).value.trim();
    const password = (document.getElementById("password") as HTMLInputElement).value;

    errorEl.style.display = "none";
    submitBtn.disabled = true;
    submitBtn.textContent = isRegister ? "Creating…" : "Signing in…";

    try {
      if (isRegister) {
        await auth.register(username, password);
        await auth.login(username, password);
      } else {
        await auth.login(username, password);
      }
      navigate("/library");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Something went wrong";
      errorEl.textContent = msg;
      errorEl.style.display = "";
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = isRegister ? "Create account" : "Sign in";
    }
  });
}
