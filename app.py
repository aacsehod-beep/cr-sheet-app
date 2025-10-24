from flask import Flask, render_template, request, redirect, session, url_for, flash
import gspread
from google.oauth2 import service_account
from datetime import datetime
import os, json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------------- Google Sheets Setup ----------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load Google credentials from Render Environment Variable
service_account_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scope)

client = gspread.authorize(creds)
sheet = client.open("crdaywise")

# ---------------- User Data ----------------
users = {
    "Dwarak": {"password": "cse2a", "section": "CSE-2A"},
    "Bhuvan": {"password": "cse2a", "section": "CSE-2A"},
    "rohith": {"password": "pass123", "section": "CSE-2B"},
    "Sowmya": {"password": "cse2b", "section": "CSE-2B"},
    "uday": {"password": "cse2c", "section": "CSE-2C"},
    "tejaswini": {"password": "cse2c", "section": "CSE-2C"},
    "sandeep": {"password": "Sandeep@12", "section": "AIML-2A"},
    "sneha": {"password": "Sneha@4", "section": "AIML-2A"},
    "rimsha": {"password": "2609", "section": "AIML-2B"},
    "Manikanta": {"password": "aiml2b", "section": "AIML-2B"},
    "Eshan123": {"password": "aiml2c", "section": "AIML-2C"},
    "charmi": {"password": "aiml2c", "section": "AIML-2C"},
    "Afeefa": {"password": "rahman", "section": "DS-2A"},
    "sai": {"password": "ds2a", "section": "DS-2A"},
    "Sonali": {"password": "cse3a", "section": "CSE-3A"},
    "Siddhartha": {"password": "cse3a", "section": "CSE-3A"},
    "Ganesh3B": {"password": "CSE3B", "section": "CSE-3B"},
    "Varshini3B": {"password": "CSE3B", "section": "CSE-3B"},
    "Akshay": {"password": "cse3c", "section": "CSE-3C"},
    "Bhavya": {"password": "cse3c", "section": "CSE-3C"},
    "VISHNU": {"password": "aiml3a", "section": "AIML-3A"},
    "NAVYA": {"password": "aiml3a", "section": "AIML-3A"},
    "Mudabbir": {"password": "AIML3B", "section": "AIML-3B"},
    "DS3A1": {"password": "ds3a", "section": "DS-3A"},
    "DS3A2": {"password": "ds3a", "section": "DS-3A"},
}

# ---------------- Routes ----------------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and user['password'] == password:
            session['username'] = username
            session['section'] = user['section']
            return redirect('/dashboard')
        else:
            flash("Invalid credentials", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect('/login')

    section = session['section']
    worksheet = sheet.worksheet(section)
    all_rows = worksheet.get_all_values()
    headers = all_rows[0]
    data_rows = all_rows[1:]

    selected_date = request.form.get('selected_date') or request.args.get('selected_date') or datetime.today().strftime('%Y-%m-%d')
    active_tab = request.form.get('active_tab') or request.args.get('active_tab') or 'submit'
    page = int(request.args.get('page', 1))
    per_page = 8

    indexed_records = []
    for i, row in enumerate(data_rows):
        record = dict(zip(headers, row))
        if record['Date'] == selected_date:
            record['row_index'] = i + 2
            indexed_records.append(record)

    total_pages = (len(indexed_records) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_records = indexed_records[start:end]

    all_dates = sorted(set(dict(zip(headers, row))['Date'] for row in data_rows), reverse=True)

    submitted_hours = [
        r['Hour'] for r in indexed_records if r['CR Name'] == session['username']
    ]

    return render_template(
        'dashboard.html',
        section=section,
        records=paginated_records,
        submitted_hours=submitted_hours,
        selected_date=selected_date,
        all_dates=all_dates,
        page=page,
        total_pages=total_pages,
        active_tab=active_tab
    )

@app.route('/submit', methods=['POST'])
def submit():
    if 'username' not in session:
        return redirect('/login')

    section = session['section']
    worksheet = sheet.worksheet(section)
    all_rows = worksheet.get_all_values()
    headers = all_rows[0]
    data_rows = all_rows[1:]

    submitted_date = request.form['date']
    hour = request.form['hour']
    cr_name = session['username']

    for row in data_rows:
        record = dict(zip(headers, row))
        if record['Date'] == submitted_date and record['CR Name'] == cr_name and record['Hour'] == hour:
            flash("You have already submitted this hour for the selected date.", "error")
            return redirect(url_for('dashboard', selected_date=submitted_date, active_tab='submit'))

    new_row = [
        submitted_date,
        cr_name,
        hour,
        request.form['scheduled_class'],
        request.form['actual_class'],
        request.form['absent_count'],
        request.form['topic_covered'],
        request.form['faculty_in'],
        request.form['faculty_out']
    ]

    insert_index = len(all_rows) + 1
    for i, row in enumerate(data_rows):
        record = dict(zip(headers, row))
        if record['Date'] > submitted_date:
            insert_index = i + 2
            break

    worksheet.insert_row(new_row, index=insert_index)
    flash("Entry submitted successfully!", "success")
    return redirect(url_for('dashboard', selected_date=submitted_date, active_tab='submit'))

@app.route('/edit/<int:row_index>', methods=['GET', 'POST'])
def edit_entry(row_index):
    if 'username' not in session:
        return redirect('/login')

    section = session['section']
    worksheet = sheet.worksheet(section)
    row_data = worksheet.row_values(row_index)

    if request.method == 'POST':
        updated_row = [
            request.form['date'],
            session['username'],
            request.form['hour'],
            request.form['scheduled_class'],
            request.form['actual_class'],
            request.form['absent_count'],
            request.form['topic_covered'],
            request.form['faculty_in'],
            request.form['faculty_out']
        ]
        worksheet.update(f'A{row_index}:I{row_index}', [updated_row])
        flash("Entry updated successfully!", "success")
        return redirect(url_for('dashboard', selected_date=request.form['date'], active_tab='view'))

    return render_template('edit.html', row=row_data, row_index=row_index)


# ---------------- Run App ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
