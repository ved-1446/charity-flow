(function () {
  var localHosts = ["localhost", "127.0.0.1"];
  var isLocalDev = location.protocol === "file:" || (localHosts.indexOf(location.hostname) !== -1 && location.port !== "8000");
  var defaultBase = isLocalDev ? "http://localhost:8000" : location.origin;
  var override = null;
  try {
    override = localStorage.getItem("cfApiBase");
  } catch (e) {
    override = null;
  }
  window.API_BASE = (override && override.trim()) ? override.trim().replace(/\/+$/, "") : defaultBase;
})();

