# Charity Flow — Complete Platform Documentation

---

## What is Charity Flow

Charity Flow is a donation management web platform built for a hackathon.
It connects donors with NGOs through an admin moderated pipeline.
Donors can submit items they want to donate, admins review and allocate
them to verified NGOs, and the entire delivery process is tracked in
real time through a simulated logistics system.

---

## What Was Built

BACKEND
- Python FastAPI server running on port 8000
- MongoDB database for all data storage using Motor async driver
- JWT based authentication — login returns a token that proves who you are
- Role based access control — admin emails are whitelisted in .env file
- Full donation pipeline: submit -> review -> allocate -> track -> deliver
- Simulated delivery system for demo purposes using background tasks
- Admin activity logging — every admin action is recorded with timestamp
- Contact message system with admin reply and flag features
- File upload system using python-multipart and multer saving to /uploads
- Test data reset endpoint for fresh starts without losing user accounts

USER FEATURES
- Donor login and JWT session management stored in localStorage
- Submit donations with photo upload, category, location and description
- My Account page showing personal donation history with live status badges
- My Messages tab showing sent contact messages and admin replies
- Drop-off History tab showing a combined timeline of all activity
- Contact form that saves messages to MongoDB
- Profile chip in hero section linking to My Account on every page

ADMIN FEATURES
- Role based access — only emails in ADMIN_EMAILS in .env get admin access
- Dashboard with live stats pulled from MongoDB in real time
- Inventory page to accept, reject and allocate donations to NGOs
- Logistics page with active/completed toggle and undo hub feature
- Cancel delivery option that reverts status back to active
- Directory page showing users, NGOs and full admin activity log
- Reports page with timeline activity history, spam log, contact messages
- Reply and flag contact messages directly from the reports page
- Profile chip on every admin page showing logged in admin and recent activity

PAGES
Admin:  admin.html, item-allocation.html, manage-users.html,
        dropoff-tracking.html, reports-history.html
User:   frontend.html, donate.html, contactus.html, ourservices.html,
        aboutus.html, myaccount.html
Shared: login.html

BACKEND FILES
main.py                   Server entry point and router registration
routes/auth.py            Login and register endpoints
routes/donations.py       Donation submission and management
routes/admin.py           Admin stats, users, NGOs, allocation
routes/logistics.py       Shipment tracking and stage updates
routes/contact.py         Contact form and message management
routes/reports.py         Activity logs, spam reports, contact messages
routes/myaccount.py       Donor personal history endpoints
middleware/auth.py        JWT token verification
middleware/admin_only.py  Admin role check
models/                   MongoDB document schemas
seed/seed_ngos.py         Pre-loads 5 fake NGOs into database
seed/seed_users.py        Pre-loads admin and donor accounts

---

## How to Start the Server (Do This Every Time)

Step 1 - Open VS Code
File -> Open Folder -> BACKSTREET TECHRUSH CHARITY FLOW -> charityflow-backend

Step 2 - Open terminal
Terminal -> New Terminal

Step 3 - Activate virtual environment
.\venv\Scripts\activate
You should see (venv) at the start of the line.
If you get an error run this first then try again:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Step 4 - Start the backend server
uvicorn main:app --reload --port 8000
You should see: Uvicorn running on http://127.0.0.1:8000
Keep this terminal open. Never close it while using the website.

Step 5 - Open the website
Go to desktop -> open BACKSTREET TECHRUSH CHARITY FLOW folder
Double click login.html to open it in your browser
OR if using Live Server in VS Code right click login.html and
select Open with Live Server

---

## Login Credentials

Demo accounts are created by the seed script (`seed/seed_users.py` or `seed/seed_all.py`).

---

## How to Reset All Test Data (Fresh Start)

Use this before demos to clear all donations, logistics, activity logs
and contact messages. User accounts and NGO data are never deleted.

Step 1 - Make sure server is running

Step 2 - Open Postman
Click the + button at the top and select HTTP

Step 3 - Get admin token
Change GET to POST using the dropdown on the left
In the URL bar type: http://localhost:8000/auth/login
Click the Body tab below the URL bar
Select raw
Change the Text dropdown on the right to JSON
Paste this in the text area:
{
  "email": "admin@charityflow.org",
  "password": "Admin@1234"
}
Click the blue Send button
In the response at the bottom find the token field
Copy the long string value inside the quotes after "token":

Step 4 - Reset the data
Click + again and select HTTP
Keep method as POST
In the URL bar type: http://localhost:8000/admin/reset-test-data
Click the Authorization tab below the URL bar
In the Type dropdown select Bearer Token
Paste your copied token in the Token field on the right
Click the blue Send button

Step 5 - Confirm success
You should see this response:
{ "message": "Test data cleared successfully" }

Collections cleared: donations, logistics_entries,
                     activity_logs, contact_messages
Collections kept:    users, ngos

---

## How to Test Any Endpoint in Postman

Step 1 - Always get a token first (see Step 3 above)
         Use admin token for admin endpoints
         Use donor token for donor endpoints

Step 2 - Create a new HTTP request
         Click + and select HTTP

Step 3 - Set the method
         GET for fetching data
         POST for creating data
         PATCH for updating data

Step 4 - Enter the URL
         Example: http://localhost:8000/donations/my-donations

Step 5 - Add the token
         Click Authorization tab
         Type dropdown: select Bearer Token
         Paste token in the Token field

Step 6 - For POST requests add body
         Click Body tab
         Select raw
         Change dropdown to JSON
         Paste your JSON data

Step 7 - Click Send and check the response

---

## Key API Endpoints Reference

AUTH
POST /auth/register              Register a new user
POST /auth/login                 Login and get JWT token

DONATIONS
POST /donate                     Submit a donation with photos
GET  /donations                  Get all donations (admin only)
GET  /donations/my-donations     Get logged in donor's donations
GET  /donations/my-history       Get donor's combined timeline
PATCH /donations/{id}/status     Update donation status (admin only)

ADMIN
GET  /admin/stats                Live dashboard stats
GET  /admin/users                All registered users
GET  /admin/ngos                 All NGOs in the system
POST /admin/allocate             Allocate donation to an NGO
GET  /admin/my-activity          Logged in admin's recent actions
GET  /admin/all-activity         All admin actions combined
POST /admin/reset-test-data      Clear all test data

LOGISTICS
GET  /logistics                  All active shipments
PATCH /logistics/{id}            Update stage (at_hub/delivered/undo_hub)
PATCH /logistics/{id}/cancel-delivery  Cancel a confirmed delivery

CONTACT
POST /contact                    Submit contact message
GET  /contact/my-messages        Logged in donor's sent messages
POST /contact/{id}/reply         Admin reply to a message
PATCH /contact/{id}/flag         Admin flag a message

REPORTS
GET  /reports/activity           Full activity log timeline
GET  /reports/spam               All rejected donations
GET  /reports/contact            All contact messages with reply status

---

## NGO Seed Data (Pre-loaded, Do Not Re-seed)

Helping Hands Trust        helpinghands@demo.ngo    Pune, MH
Bright Futures Foundation  brightfutures@demo.ngo   Mumbai, MH
Relief India Trust         relief@demo.ngo           Nagpur, MH
Udaan NGO                  udaan@demo.ngo            Delhi, NCR
Sahayata Foundation        sahayata@demo.ngo         Hyderabad, TS

---

## Troubleshooting

Problem: Login page shows unable to connect
Fix: Server is not running. Follow the start server steps above.

Problem: venv activation error
Fix: Run this first:
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
     Then run: .\venv\Scripts\activate

Problem: Postman shows 403 Forbidden
Fix: Your token has expired. Get a fresh token by logging in again.

Problem: Postman shows 401 Unauthorized
Fix: You forgot to add the Bearer Token in the Authorization tab.

Problem: Page shows failed to load data
Fix: Check server is running. Make sure you are logged in.
     Press F12 in browser, click Console tab and check for errors.

Problem: NGO dropdown is empty in inventory
Fix: NGOs were accidentally deleted. Run:
     python seed/seed_ngos.py
     This is the only seed script safe to run again.

Problem: My Account page shows no donations
Fix: Make sure you are logged in as a donor not an admin.
     Submit a donation first from the donate page.

---

## Important Notes

- MongoDB must be running before starting the server
  Check Windows Services and confirm MongoDB shows Running
- Never close the VS Code terminal while using the website
- Do NOT run seed scripts again unless NGOs are missing
- Always use POST not GET in Postman when logging in
- The server auto-reloads when you save any backend file
  so you do not need to restart after code changes
- All user accounts and NGO data are safe during resets
  Only test entries are cleared

---

## First Time Setup (Already Done - Do Not Repeat)

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install python-multipart
pip uninstall bcrypt passlib motor pymongo -y
pip install pymongo==4.6.3 motor==3.3.2 bcrypt==4.0.1 passlib==1.7.4
python seed/seed_ngos.py
python seed/seed_users.py