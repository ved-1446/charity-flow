(function () {
  // 1. HTML Escaping Utility (XSS Prevention)
  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // 2. Auth State Helpers
  function getToken() {
    try {
      return localStorage.getItem("charityToken") || "";
    } catch (e) {
      return "";
    }
  }

  function getRole() {
    try {
      return localStorage.getItem("userRole") || "";
    } catch (e) {
      return "";
    }
  }

  function getUserEmail() {
    try {
      return localStorage.getItem("userEmail") || "";
    } catch (e) {
      return "";
    }
  }

  function logout() {
    try {
      localStorage.removeItem("charityToken");
      localStorage.removeItem("userRole");
      localStorage.removeItem("userEmail");
    } catch (e) {
      console.error("Logout error clearing storage", e);
    }
    window.location.href = "login.html";
  }

  function requireLogin() {
    var token = getToken();
    if (!token) {
      try {
        sessionStorage.setItem("cfToastMessage", JSON.stringify({ message: "Please log in to continue.", type: "error" }));
      } catch (e) {}
      window.location.href = "login.html";
      return false;
    }
    return true;
  }

  function requireAdmin() {
    if (!requireLogin()) return false;
    var role = getRole();
    if (role !== "admin") {
      try {
        sessionStorage.setItem("cfToastMessage", JSON.stringify({ message: "Admin privileges required.", type: "error" }));
      } catch (e) {}
      window.location.href = "frontend.html";
      return false;
    }
    return true;
  }

  // 3. Date Formatting (Safe for ISO strings, empty values, legacy strings)
  function formatDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) {
        return String(iso);
      }
      return d.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch (e) {
      return String(iso);
    }
  }

  // 4. API Fetch Wrapper with Auth, JSON Serializing, 401 Expiry Handling
  async function apiFetch(path, options) {
    options = options || {};
    var base = (window.API_BASE || "").replace(/\/+$/, "");
    var cleanPath = path.startsWith("/") ? path : "/" + path;
    var url = path.startsWith("http://") || path.startsWith("https://") ? path : (base + cleanPath);

    var headers = Object.assign({}, options.headers || {});
    var token = getToken();
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = "Bearer " + token;
    }

    var body = options.body;
    // Automatically serialize plain object body and set JSON header
    if (body && typeof body === "object" && !(body instanceof FormData) && !(body instanceof Blob) && !(body instanceof ArrayBuffer) && !(body instanceof URLSearchParams)) {
      if (!headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
      }
      body = JSON.stringify(body);
    }

    var fetchOpts = Object.assign({}, options, {
      headers: headers,
      body: body
    });

    try {
      var res = await fetch(url, fetchOpts);
      if (res.status === 401) {
        try {
          localStorage.removeItem("charityToken");
          localStorage.removeItem("userRole");
          localStorage.removeItem("userEmail");
          sessionStorage.setItem("cfToastMessage", JSON.stringify({
            message: "Session expired. Please log in again.",
            type: "error"
          }));
        } catch (e) {}
        window.location.href = "login.html";
        return res;
      }
      return res;
    } catch (err) {
      console.error("apiFetch network error for " + url, err);
      throw err;
    }
  }

  // 5. Non-blocking Toast Notification Helper
  function showToast(message, type, duration) {
    type = type || "info"; // "info" | "success" | "error"
    duration = duration !== undefined ? duration : 4000;

    var container = document.getElementById("cf-toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "cf-toast-container";
      container.style.cssText = "position:fixed; top:20px; right:20px; z-index:99999; display:flex; flex-direction:column; gap:10px; max-width:360px; width:calc(100% - 40px); pointer-events:none;";
      document.body.appendChild(container);
    }

    var toast = document.createElement("div");
    toast.className = "cf-toast cf-toast-" + type;

    var isError = type === "error";
    toast.setAttribute("role", isError ? "alert" : "status");
    toast.setAttribute("aria-live", isError ? "assertive" : "polite");

    var bg = "#1d3557";
    if (type === "success") bg = "#2a9d8f";
    if (type === "error") bg = "#e63946";
    if (type === "warning") bg = "#f4a261";

    toast.style.cssText = "pointer-events:auto; background:" + bg + "; color:#fff; padding:12px 18px; border-radius:8px; box-shadow:0 6px 18px rgba(0,0,0,0.18); font-size:0.9rem; line-height:1.4; display:flex; justify-content:space-between; align-items:center; gap:12px; transition:opacity 0.3s ease, transform 0.3s ease; opacity:0; transform:translateY(-10px); font-family:inherit;";

    var textSpan = document.createElement("span");
    textSpan.textContent = message;
    toast.appendChild(textSpan);

    var closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.innerHTML = "&times;";
    closeBtn.setAttribute("aria-label", "Close notification");
    closeBtn.style.cssText = "background:none; border:none; color:inherit; font-size:1.3rem; line-height:1; cursor:pointer; padding:0; margin:0; opacity:0.8;";
    closeBtn.onmouseenter = function () { closeBtn.style.opacity = "1"; };
    closeBtn.onmouseleave = function () { closeBtn.style.opacity = "0.8"; };

    function removeToast() {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(-10px)";
      setTimeout(function () {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }

    closeBtn.onclick = removeToast;
    toast.appendChild(closeBtn);

    container.appendChild(toast);
    requestAnimationFrame(function () {
      toast.style.opacity = "1";
      toast.style.transform = "translateY(0)";
    });

    if (duration > 0) {
      setTimeout(removeToast, duration);
    }
    return toast;
  }

  // 6. Loading, Error, Empty State Renderers
  function renderLoading(container, message) {
    if (!container) return;
    message = message || "Loading...";
    container.innerHTML =
      '<div class="cf-state-box cf-state-loading" role="status" aria-live="polite" style="text-align:center; padding:40px 20px; color:#666;">' +
      '  <div class="cf-spinner" style="display:inline-block; width:28px; height:28px; border:3px solid #ddd; border-top-color:var(--primary-color, #1d3557); border-radius:50%; animation:cf-spin 0.8s linear infinite; margin-bottom:12px;"></div>' +
      '  <p style="margin:0; font-size:0.95rem;">' + escapeHtml(message) + '</p>' +
      '</div>';
  }

  function renderError(container, message, retryFn) {
    if (!container) return;
    message = message || "Failed to load data. Please check your connection.";
    container.innerHTML =
      '<div class="cf-state-box cf-state-error" role="alert" style="text-align:center; padding:35px 20px; color:#e63946; background:#fff5f5; border:1px solid #fed7d7; border-radius:10px; margin:15px 0;">' +
      '  <p style="margin:0 0 14px; font-weight:600; font-size:0.95rem;">' + escapeHtml(message) + '</p>' +
      '  <button type="button" class="cf-retry-btn" style="background:#1d3557; color:#fff; border:none; padding:8px 18px; border-radius:6px; cursor:pointer; font-weight:600; font-size:0.85rem; transition:background 0.2s;">Retry</button>' +
      '</div>';
    var retryBtn = container.querySelector(".cf-retry-btn");
    if (retryBtn && typeof retryFn === "function") {
      retryBtn.addEventListener("click", function () {
        renderLoading(container);
        retryFn();
      });
    }
  }

  function renderEmpty(container, message) {
    if (!container) return;
    message = message || "No records found.";
    container.innerHTML =
      '<div class="cf-state-box cf-state-empty" style="text-align:center; padding:45px 20px; color:#888; background:#fafafa; border-radius:10px; border:1px dashed #e0e0e0; margin:15px 0;">' +
      '  <p style="margin:0; font-style:italic; font-size:0.95rem;">' + escapeHtml(message) + '</p>' +
      '</div>';
  }

  // 7. Shared Hero, Tagline Rotation & Profile Chip Setup
  function initTagline(elementId, customTaglines, intervalMs) {
    var el = document.getElementById(elementId || "tagline");
    if (!el) return;
    var taglines = customTaglines && customTaglines.length > 0 ? customTaglines : [
      "Bringing kindness to every corner.",
      "Be the change you want to see.",
      "Every small help counts.",
      "Together we make a difference."
    ];
    var idx = 0;
    el.classList.add("show");
    setInterval(function () {
      el.classList.remove("show");
      setTimeout(function () {
        idx = (idx + 1) % taglines.length;
        el.textContent = taglines[idx];
        el.classList.add("show");
      }, 500);
    }, intervalMs || 4000);
  }

  function initUserProfileChip() {
    var profileEmail = document.getElementById("profileEmail");
    if (profileEmail) {
      profileEmail.textContent = getUserEmail() || "Profile";
    }
    var profileChip = document.getElementById("profileChip");
    if (profileChip && !profileChip.getAttribute("onclick")) {
      profileChip.style.cursor = "pointer";
      profileChip.onclick = function () {
        window.location.href = "myaccount.html";
      };
    }
  }

  async function initAdminProfileChip() {
    var profileEmail = document.getElementById("profileEmail");
    if (profileEmail) {
      profileEmail.textContent = getUserEmail() || "Admin";
    }
    var profileChip = document.getElementById("profileChip");
    var profileDropdown = document.getElementById("profileDropdown");
    if (!profileChip || !profileDropdown) return;

    profileChip.style.cursor = "pointer";
    profileChip.addEventListener("click", function (e) {
      e.stopPropagation();
      profileDropdown.classList.toggle("show");
    });

    document.addEventListener("click", function (e) {
      if (!profileChip.contains(e.target) && !profileDropdown.contains(e.target)) {
        profileDropdown.classList.remove("show");
      }
    });

    try {
      var res = await apiFetch("/admin/my-activity");
      if (res && res.ok) {
        var acts = await res.json();
        if (!acts || acts.length === 0) {
          profileDropdown.innerHTML = '<div class="dropdown-item">No recent activity</div>';
        } else {
          profileDropdown.innerHTML = acts.map(function (act) {
            return (
              '<div class="dropdown-item">' +
              '  <div><strong>' + escapeHtml(act.action) + '</strong>: ' + escapeHtml(act.details) + '</div>' +
              '  <div class="time">' + escapeHtml(formatDate(act.timestamp)) + '</div>' +
              '</div>'
            );
          }).join("");
        }
      }
    } catch (err) {
      console.warn("Could not load admin activity for dropdown", err);
    }
  }

  // 8. Auto-bind Logout Buttons Across All Pages
  function initLogoutButtons() {
    var btns = document.querySelectorAll("#logoutBtn, .logout-nav, .logout-btn");
    btns.forEach(function (btn) {
      btn.onclick = function (e) {
        e.preventDefault();
        logout();
      };
    });
  }

  // 9. Check for Pending Toast on Page Load (e.g. from session expiry or redirect)
  function checkStoredToast() {
    try {
      var saved = sessionStorage.getItem("cfToastMessage");
      if (saved) {
        sessionStorage.removeItem("cfToastMessage");
        var parsed = JSON.parse(saved);
        if (parsed && parsed.message) {
          showToast(parsed.message, parsed.type || "info");
        }
      }
    } catch (e) {}
  }

  // 10. Inject Global Accessible Focus and Helper Styles
  function injectCommonStyles() {
    if (document.getElementById("cf-common-styles")) return;
    var style = document.createElement("style");
    style.id = "cf-common-styles";
    style.textContent =
      "@keyframes cf-spin { 0% { transform:rotate(0deg); } 100% { transform:rotate(360deg); } }\n" +
      ":focus-visible { outline: 2px solid var(--accent-color, #457b9d) !important; outline-offset: 2px !important; }\n" +
      ".table-responsive { width:100%; overflow-x:auto; -webkit-overflow-scrolling:touch; margin-bottom:1rem; }\n" +
      ".tabs-responsive { width:100%; overflow-x:auto; -webkit-overflow-scrolling:touch; display:flex; }\n" +
      ".cf-retry-btn:hover { background:var(--accent-color, #457b9d) !important; }\n";
    document.head.appendChild(style);
  }

  // Auto-run on DOMContentLoaded
  document.addEventListener("DOMContentLoaded", function () {
    injectCommonStyles();
    initLogoutButtons();
    checkStoredToast();
  });

  // Export to window
  window.escapeHtml = escapeHtml;
  window.getToken = getToken;
  window.getRole = getRole;
  window.getUserEmail = getUserEmail;
  window.logout = logout;
  window.requireLogin = requireLogin;
  window.requireAdmin = requireAdmin;
  window.formatDate = formatDate;
  window.apiFetch = apiFetch;
  window.showToast = showToast;
  window.renderLoading = renderLoading;
  window.renderError = renderError;
  window.renderEmpty = renderEmpty;
  window.initTagline = initTagline;
  window.initUserProfileChip = initUserProfileChip;
  window.initAdminProfileChip = initAdminProfileChip;
  window.initLogoutButtons = initLogoutButtons;
})();

