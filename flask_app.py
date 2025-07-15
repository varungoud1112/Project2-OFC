from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file
import json
import os
from datetime import datetime
import requests
from functools import wraps
from collections import defaultdict
import pytz

from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# Configs
SUBMISSION_LIMIT = 1000
SUBMISSION_FILE = "submissions.json"
CLICK_LOG_FILE = "clicks.json"
LIVE_SUBMISSIONS_FILE = "live_submissions.json"
SPREADSHEET_ID = "1IU_5iT4yidGgWYBezZKOaXe1nQDVKGxCMOkaHs3_1TE"
RANGE_NAME = "Sheet1!A1"
SERVICE_ACCOUNT_FILE = "service-account.json"

# Google Sheets credentials
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheets_service = build('sheets', 'v4', credentials=credentials)

# ------------------- Utilities -------------------
def initialize_submissions():
    if not os.path.exists(SUBMISSION_FILE):
        with open(SUBMISSION_FILE, "w") as f:
            json.dump({"last_reset": datetime.today().strftime("%Y-%m-%d"), "submissions": []}, f)

def reset_if_needed():
    with open(SUBMISSION_FILE, "r") as f:
        data = json.load(f)
    today_str = datetime.today().strftime("%Y-%m-%d")
    if data.get("last_reset") != today_str:
        with open(SUBMISSION_FILE, "w") as f:
            json.dump({"last_reset": today_str, "submissions": []}, f)

def get_submission_count():
    with open(SUBMISSION_FILE, "r") as f:
        return len(json.load(f).get("submissions", []))

def store_submission(details):
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    details["timestamp"] = now_ist.strftime("%d %B %Y, %I:%M %p")

    with open(SUBMISSION_FILE, "r") as f:
        data = json.load(f)
    data["submissions"].append(details)
    with open(SUBMISSION_FILE, "w") as f:
        json.dump(data, f, indent=2)

    # ✅ Save to live_submissions.json
    live_data = []
    if os.path.exists(LIVE_SUBMISSIONS_FILE):
        with open(LIVE_SUBMISSIONS_FILE, "r") as f:
            try:
                live_data = json.load(f)
            except json.JSONDecodeError:
                pass
    live_data.append(details)
    with open(LIVE_SUBMISSIONS_FILE, "w") as f:
        json.dump(live_data, f, indent=2)

def can_submit():
    return get_submission_count() < SUBMISSION_LIMIT

def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def get_user_agent():
    return request.headers.get('User-Agent', 'Unknown')

def get_geolocation(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                return data.get("city", "Unknown"), data.get("country", "Unknown")
    except Exception as e:
        print(f"Geo lookup failed: {e}")
    return "Unknown", "Unknown"

def append_to_google_sheet(submission):
    try:
        headers = [
            "Timestamp", "Name", "Email", "Phone", "Country",
            "Course", "Message", "IP Address", "City", "Country (Geo)", "User Agent"
        ]
        sheet = sheets_service.spreadsheets().values()
        result = sheet.get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        existing_values = result.get("values", [])
        if not existing_values:
            sheet.append(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
                         valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                         body={"values": [headers]}).execute()

        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist).strftime("%d %B %Y, %I:%M %p")

        values = [[
            now_ist,
            submission.get("name", ""),
            submission.get("email", ""),
            submission.get("phone", ""),
            submission.get("country", ""),
            submission.get("course", ""),
            submission.get("comment", ""),
            submission.get("ip", ""),
            submission.get("geo_city", ""),
            submission.get("geo_country", ""),
            submission.get("user_agent", "")
        ]]

        sheet.append(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
                     valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                     body={"values": values}).execute()
    except Exception as e:
        print("❌ Sheet error:", e)

# ------------------- Click Tracker -------------------
def log_click(path):
    ip = get_client_ip()

    # ❌ Skip logging for known PythonAnywhere IPs
    if ip in ["54.242.61.254", "54.163.95.211"]:
        return

    city, country = get_geolocation(ip)

    ist = pytz.timezone("Asia/Kolkata")
    timestamp = datetime.now(ist).strftime("%Y-%m-%d %I:%M:%S %p")

    click = {
        "ip": ip,
        "city": city,
        "country": country,
        "timestamp": timestamp,
        "path": path
    }

    if not os.path.exists(CLICK_LOG_FILE):
        with open(CLICK_LOG_FILE, "w") as f:
            json.dump([], f)
    with open(CLICK_LOG_FILE, "r") as f:
        data = json.load(f)
    data.append(click)
    with open(CLICK_LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ------------------- Authentication -------------------
ADMIN_PASSWORD = "admin123"

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.args.get("key") != ADMIN_PASSWORD:
            return "Unauthorized", 403
        return f(*args, **kwargs)
    return decorated

# ------------------- Routes -------------------
@app.route('/')
def index():
    log_click("/")
    return render_template("index.html")

@app.route('/submit', methods=['POST'])
def submit_form():
    initialize_submissions()
    reset_if_needed()

    try:
        data = request.form.to_dict()
        required_fields = ["name", "email", "country", "phone", "course"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return f"❌ Missing required fields: {', '.join(missing)}", 400

        ip = get_client_ip()
        user_agent = get_user_agent()
        city, country = get_geolocation(ip)

        data.update({
            "ip": ip,
            "user_agent": user_agent,
            "geo_city": city,
            "geo_country": country
        })

        store_submission(data)
        append_to_google_sheet(data)
        log_click("/submit")

        return redirect(url_for("thank_you"))
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/thank-you')
def thank_you():
    log_click("/thank-you")
    return render_template("thank-you.html")

@app.route('/submission-count')
def submission_count():
    initialize_submissions()
    reset_if_needed()
    return f"✅ Submissions today: {get_submission_count()} / {SUBMISSION_LIMIT}"

@app.route('/admin/clicks')
@require_auth
def admin_clicks():
    if not os.path.exists(CLICK_LOG_FILE):
        clicks = []
    else:
        with open(CLICK_LOG_FILE, "r") as f:
            raw_clicks = json.load(f)

    clicks = [c for c in raw_clicks if c.get("ip") != "54.242.61.254"]

    ip_by_date = defaultdict(set)
    for click in clicks:
        try:
            dt = datetime.strptime(click.get("timestamp", ""), "%Y-%m-%d %I:%M:%S %p")
            date_str = dt.strftime("%d %B %Y")
            ip_by_date[date_str].add(click.get("ip"))
        except:
            continue

    unique_ip_count_by_date = {k: len(v) for k, v in ip_by_date.items()}
    location_summary = defaultdict(lambda: defaultdict(int))
    for click in clicks:
        try:
            dt = datetime.strptime(click.get("timestamp", ""), "%Y-%m-%d %I:%M:%S %p")
            date_str = dt.strftime("%d %B %Y")
            loc = f"{click.get('city', 'Unknown')}, {click.get('country', 'Unknown')}"
            location_summary[date_str][loc] += 1
        except:
            continue

    return render_template(
        "clicks.html",
        clicks=clicks,
        total_unique_ips=len(set(click.get("ip") for click in clicks)),
        location_summary=dict(location_summary),
        unique_ip_by_date=dict(ip_by_date),
        unique_ip_count_by_date=unique_ip_count_by_date
    )

@app.route('/admin/live-submissions')
@require_auth
def view_live_submissions():
    if not os.path.exists(LIVE_SUBMISSIONS_FILE):
        return "No submissions yet."
    with open(LIVE_SUBMISSIONS_FILE, "r") as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/admin/download/live-submissions')
@require_auth
def download_live_submissions():
    if not os.path.exists(LIVE_SUBMISSIONS_FILE):
        return "No submissions to download."
    return send_file(LIVE_SUBMISSIONS_FILE, as_attachment=True)

@app.route('/admin/clicks/data')
@require_auth
def get_clicks_data():
    with open(CLICK_LOG_FILE, "r") as f:
        clicks = json.load(f)
    unique_ips = set(click["ip"] for click in clicks)
    return jsonify({
        "clicks": clicks,
        "total_unique_ips": len(unique_ips)
    })

# ------------------- Main -------------------
if __name__ == '__main__':
    app.run(debug=True)
