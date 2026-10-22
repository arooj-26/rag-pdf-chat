/* Session state stays in memory; HttpOnly credentials are sent by the browser. */
(() => {
  const nativeFetch = window.fetch.bind(window);
  let csrf = "";
  const isAuthPage = ["/login", "/register", "/"].includes(location.pathname);
  const ready = nativeFetch("/api/auth/me", {credentials: "same-origin"}).then(async response => {
    if (response.ok) {
      const user = await response.json();
      csrf = user.csrf_token;
      return user;
    }
    if (!isAuthPage) location.replace("/login");
    return null;
  });
  window.researchAuth = {ready, csrf: () => csrf};
  window.fetch = async (input, options = {}) => {
    const url = new URL(typeof input === "string" ? input : input.url, location.href);
    if (url.origin === location.origin && url.pathname.startsWith("/api/")) {
      await ready;
      const headers = new Headers(options.headers || {});
      if (!["GET", "HEAD", "OPTIONS"].includes((options.method || "GET").toUpperCase())) headers.set("X-CSRF-Token", csrf);
      options = {...options, headers, credentials: "same-origin"};
    }
    const response = await nativeFetch(input, options);
    if (response.status === 401 && !isAuthPage) location.replace("/login");
    return response;
  };
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-logout]").forEach(button => button.addEventListener("click", async () => {
      const response = await fetch("/api/auth/logout", {method: "POST"});
      if (response.ok) location.assign("/login");
    }));
    const form = document.getElementById("auth-form");
    form?.addEventListener("submit", async event => {
      event.preventDefault();
      const button = form.querySelector("button[type=submit]");
      const error = document.getElementById("auth-error");
      button.disabled = true;
      error.textContent = "Signing in…";
      try {
        const response = await nativeFetch(`/api/auth/${form.dataset.action}`, {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({email: form.email.value, password: form.password.value})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Check your email and password (12–128 characters).");
        location.assign("/dashboard");
      } catch (err) { error.textContent = err.message; }
      finally { button.disabled = false; }
    });
  });
})();
