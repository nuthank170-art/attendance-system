from flask import Flask, render_template, request, redirect, send_file
import sqlite3, os, base64, requests
import pytz
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import PatternFill

app = Flask(__name__)

# ---------------- SUPABASE ----------------

SUPABASE_URL = "https://odbkrbarwhhzfemqfbts.supabase.co"
SUPABASE_KEY = "sb_publishable_9xNlO3TyVXlolLDhjIuuFw_wqdHCTYh"

# upload image to supabase storage
def upload_image_to_supabase(image_data, filename):

    img_data = base64.b64decode(image_data.split(",")[1])

    url = f"{SUPABASE_URL}/storage/v1/object/public/attendance-images/{filename}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "image/jpeg"
    }

    r = requests.post(url, headers=headers, data=img_data)

    print("IMAGE UPLOAD:", r.status_code, r.text)

    return url

# save row in supabase table
def send_to_supabase(emp_id,name,date,time,image_url):

    url = f"{SUPABASE_URL}/rest/v1/attendance"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    data = {
        "employee_id": emp_id,
        "name": name,
        "date": f"{date} {time}",
        "image_url": image_url
    }

    r = requests.post(url, json=data, headers=headers)

    print("DB INSERT:", r.status_code, r.text)

# ---------------- LOCAL DATABASE ----------------

def db():
    return sqlite3.connect("database.db")

def create_tables():

    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees(
    id TEXT,
    name TEXT,
    designation TEXT,
    location TEXT)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
    emp_id TEXT,
    date TEXT,
    in_time TEXT,
    out_time TEXT,
    gps TEXT)
    """)

    con.commit()

create_tables()

# ---------------- ROUTES ----------------

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    con=db()
    cur=con.cursor()

    cur.execute("select * from employees")
    data=cur.fetchall()

    return render_template("dashboard.html", employees=data)

@app.route("/add_employee",methods=["GET","POST"])
def add_employee():

    if request.method=="POST":

        con=db()
        cur=con.cursor()

        cur.execute(
        "insert into employees values(?,?,?,?)",
        (
        request.form["id"],
        request.form["name"],
        request.form["designation"],
        request.form["location"]
        )
        )

        con.commit()

        return redirect("/dashboard")

    return render_template("add_employee.html")

@app.route("/attendance/<emp_id>", methods=["GET","POST"])
def attendance(emp_id):

    india = pytz.timezone("Asia/Kolkata")

    con = db()
    cur = con.cursor()

    cur.execute("select name from employees where id=?", (emp_id,))
    emp = cur.fetchone()

    emp_name = emp[0] if emp else emp_id

    if request.method == "POST":

        type = request.form["type"]
        img = request.form["image"]
        gps = request.form.get("location","")

        now = datetime.now(india)

        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        cur.execute(
        "SELECT * FROM attendance WHERE emp_id=? AND date=?",
        (emp_id,date)
        )

        row = cur.fetchone()

        filename = f"{emp_id}_{date}_{time}.jpg"

        image_url = upload_image_to_supabase(img, filename)

        # ---------- IN ----------

        if type=="IN":

            if row:
                return redirect(f"/attendance/{emp_id}")

            cur.execute(
            "INSERT INTO attendance VALUES (?,?,?,?,?)",
            (emp_id,date,time,"",gps)
            )

            send_to_supabase(emp_id,emp_name,date,time,image_url)

        # ---------- OUT ----------

        else:

            if not row:
                return redirect(f"/attendance/{emp_id}")

            if row[3]!="":
                return redirect(f"/attendance/{emp_id}")

            cur.execute(
            """
            UPDATE attendance
            SET out_time=?, gps=?
            WHERE emp_id=? AND date=?
            """,
            (time,gps,emp_id,date)
            )

            send_to_supabase(emp_id,emp_name,date,time,image_url)

        con.commit()

        return redirect(f"/attendance/{emp_id}")

    cur.execute(
    """
    SELECT in_time,out_time
    FROM attendance
    WHERE emp_id=?
    ORDER BY date DESC
    LIMIT 1
    """,
    (emp_id,)
    )

    row = cur.fetchone()

    in_time=""
    out_time=""

    if row:
        in_time=row[0]
        out_time=row[1]

    return render_template(
    "attendance.html",
    emp_id=emp_id,
    in_time=in_time,
    out_time=out_time
    )

# ---------------- RUN ----------------

if __name__=="__main__":

    port=int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0",port=port)
