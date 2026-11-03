(function () {
  // In single-URL deployment, FastAPI serves the frontend from the same origin.
  // When opened via file://, fall back to http://localhost:8000.
  var defaultBase = location.protocol === "file:" ? "http://localhost:8000" : location.origin;
  var override = null;
  try {
    override = localStorage.getItem("cfApiBase");
  } catch (e) {
    override = null;
  }
  window.API_BASE = (override && override.trim()) ? override.trim().replace(/\/+$/, "") : defaultBase;
})();
