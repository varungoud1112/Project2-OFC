# 📋 Real-Time Course Inquiry Tracker

This is a Flask-based web application designed to manage real-time course inquiry submissions. It integrates with Google Sheets for storing data, tracks user clicks, and logs geolocation, IP, and device info. It includes an admin panel with secure endpoints to monitor clicks and download submission data.

## 🚀 Features

- ✅ Real-time submission tracking (limit: 1000/day)
- 📄 Google Sheets integration using Service Account
- 📍 IP geolocation tracking (City, Country)
- 📱 User agent logging
- 🔒 Admin dashboard with authentication
- 📊 Click tracking with location summary
- 💾 JSON-based data storage (submissions, clicks, live entries)
- ⏰ Auto-reset submissions daily (based on server time)

---

## 🛠️ Tech Stack

- Python 3.x
- Flask
- Google Sheets API (v4)
- JSON for local storage
- HTML templates for UI
- Bootstrap (optional for styling)
- IP-API for geolocation

---

## 📁 Project Structure

```
├── app.py
├── templates/
│   ├── index.html
│   ├── thank-you.html
│   └── clicks.html
├── service-account.json  # Google API credentials
├── submissions.json
├── live_submissions.json
├── clicks.json
└── requirements.txt
```

---

## 🧪 How to Run Locally

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/your-repo.git
   cd your-repo
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows use venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add Your `service-account.json`**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Google Sheets API
   - Create a service account and download the JSON credentials
   - Share the Google Sheet with the service account email (edit access)

5. **Run the App**
   ```bash
   python app.py
   ```

6. **Access the Web App**
   - Visit `http://127.0.0.1:5000` in your browser

---

## 🔐 Admin Access

To access admin routes, append `?key=admin123` to the URL.  
For example:
- `http://localhost:5000/admin/clicks?key=admin123`
- `http://localhost:5000/admin/live-submissions?key=admin123`

You can change the password in the source code:
```python
ADMIN_PASSWORD = "admin123"
```

---

## 📈 Example Admin Dashboard

- View all user clicks with location and timestamp
- Count unique IPs by date
- See real-time submissions
- Download full submission logs

---

## 📦 Requirements

```
Flask
pytz
google-api-python-client
google-auth
requests
```

> All dependencies are listed in `requirements.txt`.

---

## 📬 Contact

For any queries or suggestions, feel free to reach out!

---

## 📝 License

This project is open-source and available under the MIT License.