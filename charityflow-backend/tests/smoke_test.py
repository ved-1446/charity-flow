import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
from jose import jwt
from config import JWT_SECRET

# Target server base URL
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TEST_BASE_URL", "http://127.0.0.1:8001")
print(f"Running Charity Flow Smoke Test against: {BASE_URL}")

results = []

def record(test_num: int, method: str, endpoint: str, role: str, expected: str, actual: str, status: str, notes: str = ""):
    results.append({
        "num": test_num,
        "method": method,
        "endpoint": endpoint,
        "role": role,
        "expected": expected,
        "actual": actual,
        "status": status,
        "notes": notes
    })

def make_expired_token(email: str = "donor@charityflow.org", role: str = "donor") -> str:
    expired_time = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {"email": email, "role": role, "exp": expired_time}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def run_tests():
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)
    test_id = 1

    # 1. Health check
    try:
        r = client.get("/health")
        exp = "200"
        act = str(r.status_code)
        st = "PASS" if r.status_code == 200 and r.json().get("status") == "ok" else "FAIL"
        record(test_id, "GET", "/health", "None", exp, act, st, f"DB status: {r.json().get('db')}")
    except Exception as e:
        record(test_id, "GET", "/health", "None", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 2. Root check
    try:
        r = client.get("/")
        st = "PASS" if r.status_code == 200 else "FAIL"
        record(test_id, "GET", "/", "None", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/", "None", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 3. Missing token on protected route -> 401 with WWW-Authenticate
    try:
        r = client.get("/admin/stats")
        auth_hdr = r.headers.get("www-authenticate", "")
        st = "PASS" if r.status_code == 401 and "Bearer" in auth_hdr else "FAIL"
        record(test_id, "GET", "/admin/stats", "No Token", "401 + WWW-Auth", f"{r.status_code} ({auth_hdr})", st)
    except Exception as e:
        record(test_id, "GET", "/admin/stats", "No Token", "401", "ERR", "FAIL", str(e))
    test_id += 1

    # 4. Invalid token -> 401 with detail "Invalid token"
    try:
        r = client.get("/admin/stats", headers={"Authorization": "Bearer totally_bogus_token"})
        det = r.json().get("detail", "")
        st = "PASS" if r.status_code == 401 and "invalid" in det.lower() else "FAIL"
        record(test_id, "GET", "/admin/stats", "Invalid Token", "401 (Invalid token)", f"{r.status_code} ({det})", st)
    except Exception as e:
        record(test_id, "GET", "/admin/stats", "Invalid Token", "401", "ERR", "FAIL", str(e))
    test_id += 1

    # 5. Expired token -> 401 with detail "Token expired"
    try:
        expired_tok = make_expired_token()
        r = client.get("/admin/stats", headers={"Authorization": f"Bearer {expired_tok}"})
        det = r.json().get("detail", "")
        st = "PASS" if r.status_code == 401 and "expired" in det.lower() else "FAIL"
        record(test_id, "GET", "/admin/stats", "Expired Token", "401 (Token expired)", f"{r.status_code} ({det})", st)
    except Exception as e:
        record(test_id, "GET", "/admin/stats", "Expired Token", "401", "ERR", "FAIL", str(e))
    test_id += 1

    # 6. Admin Login
    admin_token = None
    try:
        r = client.post("/auth/login", json={"email": "admin@charityflow.org", "password": "Admin@1234"})
        if r.status_code == 200 and r.json().get("role") == "admin":
            admin_token = r.json().get("token")
            st = "PASS"
        else:
            st = "FAIL"
        record(test_id, "POST", "/auth/login", "admin", "200 + token", str(r.status_code), st, "Admin authentication")
    except Exception as e:
        record(test_id, "POST", "/auth/login", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 7. Donor Login
    donor_token = None
    try:
        r = client.post("/auth/login", json={"email": "donor@charityflow.org", "password": "Donor@1234"})
        if r.status_code == 200 and r.json().get("role") == "donor":
            donor_token = r.json().get("token")
            st = "PASS"
        else:
            st = "FAIL"
        record(test_id, "POST", "/auth/login", "donor", "200 + token", str(r.status_code), st, "Donor authentication")
    except Exception as e:
        record(test_id, "POST", "/auth/login", "donor", "200", "ERR", "FAIL", str(e))
    test_id += 1

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    donor_headers = {"Authorization": f"Bearer {donor_token}"}

    # 8. Donor Forbidden on Admin Routes (Check 403)
    admin_routes_to_test = [
        ("GET", "/donations"),
        ("GET", "/admin/stats"),
        ("GET", "/admin/actions-today"),
        ("GET", "/admin/users"),
        ("GET", "/admin/ngos"),
        ("POST", "/admin/allocate", {"donation_id": "000000000000000000000000", "ngo_email": "test@demo.ngo"}),
        ("GET", "/admin/my-activity"),
        ("GET", "/admin/all-activity"),
        ("POST", "/admin/reset-test-data", {}),
        ("GET", "/logistics"),
        ("PATCH", "/logistics/000000000000000000000000", {"stage": "at_hub"}),
        ("PATCH", "/logistics/000000000000000000000000/cancel-delivery", {"reason": "test"}),
        ("POST", "/contact/000000000000000000000000/reply", {"reply": "test"}),
        ("PATCH", "/contact/000000000000000000000000/flag", {}),
        ("GET", "/reports/activity"),
        ("GET", "/reports/spam"),
        ("GET", "/reports/contact"),
    ]

    for item in admin_routes_to_test:
        method = item[0]
        path = item[1]
        body = item[2] if len(item) > 2 else None
        try:
            if method == "GET":
                r = client.get(path, headers=donor_headers)
            elif method == "POST":
                r = client.post(path, headers=donor_headers, json=body or {})
            elif method == "PATCH":
                r = client.patch(path, headers=donor_headers, json=body or {})
            st = "PASS" if r.status_code == 403 else "FAIL"
            record(test_id, method, path, "donor (403 check)", "403", str(r.status_code), st)
        except Exception as e:
            record(test_id, method, path, "donor (403 check)", "403", "ERR", "FAIL", str(e))
        test_id += 1

    # 9. File upload validation on POST /donate
    # 9a. Non-image file (HTML file)
    try:
        files = {"photos": ("malicious.html", b"<html><body><script>alert(1)</script></body></html>", "text/html")}
        data = {"location": "Mumbai", "category": "Books", "description": "HTML file injection attempt"}
        r = client.post("/donate", headers=donor_headers, data=data, files=files)
        st = "PASS" if r.status_code == 400 else "FAIL"
        record(test_id, "POST", "/donate", "donor", "400", str(r.status_code), st, "Reject .html file")
    except Exception as e:
        record(test_id, "POST", "/donate", "donor", "400", "ERR", "FAIL", str(e))
    test_id += 1

    # 9b. Fake extension (.png containing ASCII text without magic bytes)
    try:
        files = {"photos": ("fake.png", b"This is not a real PNG file at all", "image/png")}
        data = {"location": "Mumbai", "category": "Books", "description": "Corrupt magic bytes"}
        r = client.post("/donate", headers=donor_headers, data=data, files=files)
        st = "PASS" if r.status_code == 400 else "FAIL"
        record(test_id, "POST", "/donate", "donor", "400", str(r.status_code), st, "Reject spoofed extension without real magic bytes")
    except Exception as e:
        record(test_id, "POST", "/donate", "donor", "400", "ERR", "FAIL", str(e))
    test_id += 1

    # 9c. Oversized file (> 5 MB)
    try:
        large_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * (5 * 1024 * 1024 + 100))
        files = {"photos": ("huge.png", large_bytes, "image/png")}
        data = {"location": "Mumbai", "category": "Books", "description": "Oversized upload"}
        r = client.post("/donate", headers=donor_headers, data=data, files=files)
        st = "PASS" if r.status_code == 400 else "FAIL"
        record(test_id, "POST", "/donate", "donor", "400", str(r.status_code), st, "Reject oversize file (>5MB)")
    except Exception as e:
        record(test_id, "POST", "/donate", "donor", "400", "ERR", "FAIL", str(e))
    test_id += 1

    # 9d. Valid PNG upload with real signature
    valid_png_bytes = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082")
    created_donation_id = None
    try:
        files = {"photos": ("winter_jacket.png", valid_png_bytes, "image/png")}
        data = {"location": "123 Hope Street", "category": "Clothing", "description": "Real donation test"}
        r = client.post("/donate", headers=donor_headers, data=data, files=files)
        if r.status_code == 200 and r.json().get("donation_id"):
            created_donation_id = r.json().get("donation_id")
            st = "PASS"
        else:
            st = "FAIL"
        record(test_id, "POST", "/donate", "donor", "200 + donation_id", str(r.status_code), st, f"Created ID: {created_donation_id}")
    except Exception as e:
        record(test_id, "POST", "/donate", "donor", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 10. GET /donations/{id} access control
    # 10a. Donor views their own donation -> 200
    try:
        r = client.get(f"/donations/{created_donation_id}", headers=donor_headers)
        st = "PASS" if r.status_code == 200 and r.json().get("_id") == created_donation_id else "FAIL"
        record(test_id, "GET", "/donations/{id}", "donor (owner)", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/donations/{id}", "donor (owner)", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 10b. Another donor views it -> 403
    try:
        other_donor_tok = jwt.encode({"email": "donor2@charityflow.org", "role": "donor", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, JWT_SECRET, algorithm="HS256")
        r = client.get(f"/donations/{created_donation_id}", headers={"Authorization": f"Bearer {other_donor_tok}"})
        st = "PASS" if r.status_code == 403 else "FAIL"
        record(test_id, "GET", "/donations/{id}", "donor (non-owner)", "403", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/donations/{id}", "donor (non-owner)", "403", "ERR", "FAIL", str(e))
    test_id += 1

    # 10c. Admin views it -> 200
    try:
        r = client.get(f"/donations/{created_donation_id}", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and r.json().get("_id") == created_donation_id else "FAIL"
        record(test_id, "GET", "/donations/{id}", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/donations/{id}", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 11. GET /donations/my-donations
    try:
        r = client.get("/donations/my-donations", headers=donor_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/donations/my-donations", "donor", "200 (list)", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/donations/my-donations", "donor", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 12. GET /donations/my-history
    try:
        r = client.get("/donations/my-history", headers=donor_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/donations/my-history", "donor", "200 (list)", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/donations/my-history", "donor", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 13. Admin lists all donations: GET /donations
    try:
        r = client.get("/donations", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/donations", "admin", "200 (list)", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/donations", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 14. Admin updates status: PATCH /donations/{id}/status
    try:
        r = client.patch(f"/donations/{created_donation_id}/status", headers=admin_headers, json={"status": "accepted"})
        st = "PASS" if r.status_code == 200 else "FAIL"
        record(test_id, "PATCH", "/donations/{id}/status", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "PATCH", "/donations/{id}/status", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 15. Admin gets NGOs: GET /admin/ngos
    target_ngo_email = "helpinghands@demo.ngo"
    try:
        r = client.get("/admin/ngos", headers=admin_headers)
        if r.status_code == 200 and len(r.json()) > 0:
            target_ngo_email = r.json()[0].get("email", target_ngo_email)
            st = "PASS"
        else:
            st = "FAIL"
        record(test_id, "GET", "/admin/ngos", "admin", "200", str(r.status_code), st, f"NGO count: {len(r.json()) if r.status_code == 200 else 0}")
    except Exception as e:
        record(test_id, "GET", "/admin/ngos", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 16. Admin allocates donation: POST /admin/allocate
    try:
        r = client.post("/admin/allocate", headers=admin_headers, json={"donation_id": created_donation_id, "ngo_email": target_ngo_email})
        st = "PASS" if r.status_code == 200 else "FAIL"
        record(test_id, "POST", "/admin/allocate", "admin", "200", str(r.status_code), st, f"Allocated to {target_ngo_email}")
    except Exception as e:
        record(test_id, "POST", "/admin/allocate", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 17. Admin checks logistics: GET /logistics
    try:
        r = client.get("/logistics", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/logistics", "admin", "200 (list)", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/logistics", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 18. Admin advances logistics stage: PATCH /logistics/{donation_id}
    try:
        r = client.patch(f"/logistics/{created_donation_id}", headers=admin_headers, json={"stage": "at_hub"})
        st = "PASS" if r.status_code == 200 else "FAIL"
        record(test_id, "PATCH", "/logistics/{id}", "admin", "200", str(r.status_code), st, "Stage moved to at_hub")
    except Exception as e:
        record(test_id, "PATCH", "/logistics/{id}", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 19. Admin cancels delivery: PATCH /logistics/{donation_id}/cancel-delivery
    try:
        r = client.patch(f"/logistics/{created_donation_id}/cancel-delivery", headers=admin_headers, json={"reason": "Temporary weather delay"})
        st = "PASS" if r.status_code == 200 else "FAIL"
        record(test_id, "PATCH", "/logistics/{id}/cancel-delivery", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "PATCH", "/logistics/{id}/cancel-delivery", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 20. Donor submits contact message: POST /contact
    contact_msg_id = None
    try:
        r = client.post("/contact", json={"name": "Generous Donor", "email": "donor@charityflow.org", "message": "Smoke test contact message"})
        st = "PASS" if r.status_code == 200 else "FAIL"
        record(test_id, "POST", "/contact", "public/donor", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "POST", "/contact", "public/donor", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 21. Donor checks my messages: GET /contact/my-messages
    try:
        r = client.get("/contact/my-messages", headers=donor_headers)
        if r.status_code == 200 and len(r.json()) > 0:
            contact_msg_id = r.json()[0].get("message_id")
            st = "PASS"
        else:
            st = "FAIL"
        record(test_id, "GET", "/contact/my-messages", "donor", "200", str(r.status_code), st, f"Found message ID: {contact_msg_id}")
    except Exception as e:
        record(test_id, "GET", "/contact/my-messages", "donor", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 22. Admin reports endpoints
    # 22a. GET /reports/activity
    try:
        r = client.get("/reports/activity", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/reports/activity", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/reports/activity", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 22b. GET /reports/spam
    try:
        r = client.get("/reports/spam", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/reports/spam", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/reports/spam", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 22c. GET /reports/contact
    try:
        r = client.get("/reports/contact", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/reports/contact", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/reports/contact", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 23. Admin flags contact message: PATCH /contact/{id}/flag
    if contact_msg_id:
        try:
            r = client.patch(f"/contact/{contact_msg_id}/flag", headers=admin_headers)
            st = "PASS" if r.status_code == 200 else "FAIL"
            record(test_id, "PATCH", "/contact/{id}/flag", "admin", "200", str(r.status_code), st)
        except Exception as e:
            record(test_id, "PATCH", "/contact/{id}/flag", "admin", "200", "ERR", "FAIL", str(e))
        test_id += 1

        # 24. Admin replies to contact message: POST /contact/{id}/reply
        try:
            r = client.post(f"/contact/{contact_msg_id}/reply", headers=admin_headers, json={"reply": "Smoke test reply from admin"})
            st = "PASS" if r.status_code == 200 else "FAIL"
            record(test_id, "POST", "/contact/{id}/reply", "admin", "200", str(r.status_code), st)
        except Exception as e:
            record(test_id, "POST", "/contact/{id}/reply", "admin", "200", "ERR", "FAIL", str(e))
        test_id += 1

        # 25. Donor sees reply in /contact/my-messages
        try:
            r = client.get("/contact/my-messages", headers=donor_headers)
            msgs = r.json() if r.status_code == 200 else []
            found = any(m.get("message_id") == contact_msg_id and m.get("status") == "replied" and m.get("reply") for m in msgs)
            st = "PASS" if found else "FAIL"
            record(test_id, "GET", "/contact/my-messages", "donor", "Reply visible", "Verified" if found else "Missing", st)
        except Exception as e:
            record(test_id, "GET", "/contact/my-messages", "donor", "Reply visible", "ERR", "FAIL", str(e))
        test_id += 1

    # 26. Admin dashboard stats & actions today
    # 26a. GET /admin/stats
    try:
        r = client.get("/admin/stats", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and "pending_count" in r.json() else "FAIL"
        record(test_id, "GET", "/admin/stats", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/admin/stats", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 26b. GET /admin/actions-today
    try:
        r = client.get("/admin/actions-today", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and "actions_today" in r.json() else "FAIL"
        record(test_id, "GET", "/admin/actions-today", "admin", "200", str(r.status_code), st, f"Actions today: {r.json().get('actions_today')}")
    except Exception as e:
        record(test_id, "GET", "/admin/actions-today", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 26c. GET /admin/my-activity
    try:
        r = client.get("/admin/my-activity", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/admin/my-activity", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/admin/my-activity", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 26d. GET /admin/all-activity
    try:
        r = client.get("/admin/all-activity", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/admin/all-activity", "admin", "200", str(r.status_code), st)
    except Exception as e:
        record(test_id, "GET", "/admin/all-activity", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 26e. GET /admin/users
    try:
        r = client.get("/admin/users", headers=admin_headers)
        st = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
        record(test_id, "GET", "/admin/users", "admin", "200", str(r.status_code), st, f"Total users: {len(r.json()) if r.status_code == 200 else 0}")
    except Exception as e:
        record(test_id, "GET", "/admin/users", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # 27. User model validation (Pydantic email/password rules)
    # 27a. Invalid email format rejected
    try:
        r = client.post("/auth/register", json={"email": "not-an-email", "password": "Password@123"})
        st = "PASS" if r.status_code == 422 else "FAIL"
        record(test_id, "POST", "/auth/register", "public", "422", str(r.status_code), st, "Invalid email format rejected")
    except Exception as e:
        record(test_id, "POST", "/auth/register", "public", "422", "ERR", "FAIL", str(e))
    test_id += 1

    # 27b. Short password (<8 chars) rejected
    try:
        r = client.post("/auth/register", json={"email": "validuser@charityflow.org", "password": "123"})
        st = "PASS" if r.status_code == 422 else "FAIL"
        record(test_id, "POST", "/auth/register", "public", "422", str(r.status_code), st, "Short password rejected (<8 chars)")
    except Exception as e:
        record(test_id, "POST", "/auth/register", "public", "422", "ERR", "FAIL", str(e))
    test_id += 1

    # 28. POST /admin/reset-test-data (Admin only, succeeds when DEMO_MODE is true)
    try:
        r = client.post("/admin/reset-test-data", headers=admin_headers)
        st = "PASS" if r.status_code == 200 else "FAIL"
        record(test_id, "POST", "/admin/reset-test-data", "admin", "200", str(r.status_code), st, "Reset test data executed")
    except Exception as e:
        record(test_id, "POST", "/admin/reset-test-data", "admin", "200", "ERR", "FAIL", str(e))
    test_id += 1

    # Print Table
    print("\n" + "="*115)
    print(f"{'#':<3} | {'METHOD':<6} | {'ENDPOINT':<38} | {'ROLE':<22} | {'EXPECTED':<12} | {'ACTUAL':<12} | {'STATUS'}")
    print("="*115)
    passed_count = 0
    failed_count = 0
    for res in results:
        if res['status'] == 'PASS':
            passed_count += 1
        else:
            failed_count += 1
        print(f"{res['num']:<3} | {res['method']:<6} | {res['endpoint']:<38} | {res['role']:<22} | {res['expected']:<12} | {res['actual']:<12} | {res['status']}")
    print("="*115)
    print(f"TOTAL TESTS: {len(results)} | PASSED: {passed_count} | FAILED: {failed_count}")
    print("="*115)

    if failed_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()

