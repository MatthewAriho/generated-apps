import { auth } from "../api";
import { navigate } from "../router";

export function renderLogin(): string {
  return `
    <div class="login-page">
      <div class="login-hero">
        <div class="login-logo">&#127866;</div>
        <h1 class="login-title">Taplord</h1>
        <p class="login-subtitle">Competitive beer tracking for legends</p>
      </div>

      <div class="login-card">
        <div class="login-tabs">
          <button class="login-tab active" data-tab="login">Log In</button>
          <button class="login-tab" data-tab="register">Sign Up</button>
        </div>

        <form id="login-form" class="login-form" autocomplete="off">
          <div class="form-group">
            <label for="login-username">Username</label>
            <input type="text" id="login-username" name="username" placeholder="your_username" required autocapitalize="none" autocorrect="off" />
          </div>
          <div class="form-group">
            <label for="login-password">Password</label>
            <input type="password" id="login-password" name="password" placeholder="password" required />
          </div>
          <div class="form-group register-only" style="display:none">
            <label for="login-display-name">Display Name (optional)</label>
            <input type="text" id="login-display-name" name="display_name" placeholder="How others see you" />
          </div>
          <div id="login-error" class="form-error" style="display:none"></div>
          <button type="submit" class="btn btn-primary btn-large" id="login-submit">
            Log In
          </button>
        </form>
      </div>

      <p class="login-footer">Track your beers. Climb the ranks. &#127942;</p>
    </div>
  `;
}

export function initLogin(): void {
  let mode: "login" | "register" = "login";

  const tabs = document.querySelectorAll(".login-tab");
  const registerFields = document.querySelectorAll(".register-only") as NodeListOf<HTMLElement>;
  const submitBtn = document.getElementById("login-submit") as HTMLButtonElement;
  const form = document.getElementById("login-form") as HTMLFormElement;
  const errorEl = document.getElementById("login-error") as HTMLElement;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      mode = tab.getAttribute("data-tab") as "login" | "register";
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      registerFields.forEach((f) => (f.style.display = mode === "register" ? "block" : "none"));
      submitBtn.textContent = mode === "login" ? "Log In" : "Create Account";
      errorEl.style.display = "none";
    });
  });

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.style.display = "none";
    submitBtn.disabled = true;
    submitBtn.textContent = mode === "login" ? "Logging in..." : "Creating account...";

    const username = (document.getElementById("login-username") as HTMLInputElement).value.trim();
    const password = (document.getElementById("login-password") as HTMLInputElement).value;
    const displayName = (document.getElementById("login-display-name") as HTMLInputElement).value.trim();

    try {
      if (mode === "login") {
        await auth.login(username, password);
      } else {
        await auth.register(username, password, displayName || undefined);
      }
      navigate("/home");
    } catch (err: any) {
      errorEl.textContent = err.message || "Something went wrong";
      errorEl.style.display = "block";
      submitBtn.disabled = false;
      submitBtn.textContent = mode === "login" ? "Log In" : "Create Account";
    }
  });
}
