from flask import Flask, render_template, request, redirect
import os, base64, requests
import pytz
from datetime import datetime

app = Flask(__name__)

# ---------------- SUPABASE ----------------

SUPABASE_URL = "https://odbkrbarwhhzfemqfbts.supabase.co"
SUPABASE_KEY = "sb_publishable_9xNlO3TyVXlolLDhjIuuFw_wqdHCTYh"

BUCKET = "attendance-images"


# ---------------- IMAGE UPLOAD ----------------

def upload_image_to_supabase(image_data, filename):

    img_data = base64.b64decode(image_data.split(",")[1])

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "image/jpeg"
    }

    r = requests.post(upload_url, headers=headers, data=img_data)

    print("IMAGE:", r.status_code, r.text)

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{filename}"

    return public_url


# ---------------- EMPLOYEE ----------------

def get_employees():

    url = f"{SUPABASE_URL}/rest/v1/employees?select=*"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    r = requests.get(url, headers=headers)

    return r.json()


def save_employee(emp_id,name,designation,location):

    url = f"{SUPABASE_URL}/rest/v1/employees"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "id": emp_id,
        "name": name,
        "designation": designation,
        "location": location
    }

    r = requests.post(url, json=data, headers=headers)

    print("EMP:", r.status_code, r.text)


# ---------------- ATTENDANCE ----------------

def get_today_record(emp_id,date):

    url = f"{SUPABASE_URL}/rest/v1/attendance?employee_id=eq.{emp_id}&date=eq.{date}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    r = requests.get(url, headers=headers)

    data = r.json()

    if len(data)>0:

        return data[0]

    return None


def save_in(emp_id,name,date,time,image_url):

    url = f"{SUPABASE_URL}/rest/v1/attendance"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "employee_id": emp_id,
        "name": name,
        "date": date,
        "in_time": time,
        "in_image": image_url
    }

    requests.post(url,json=data,headers=headers)


def save_out(emp_id,date,time,image_url):

    url = f"{SUPABASE_URL}/rest/v1/attendance?employee_id=eq.{emp_id}&date=eq.{date}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "out_time": time,
        "out_image": image_url
    }

    requests.patch(url,json=data,headers=headers)


def get_last_photo(emp_id):

    url = f"{SUPABASE_URL}/rest/v1/attendance?employee_id=eq.{emp_id}&order=date.desc&limit=1"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    r = requests.get(url, headers=headers)

    data = r.json()

    if len(data)>0:

        return data[0].get("in_image","")

    return ""


# ---------------- ROUTES ----------------

@app.route("/")
def login():

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    employees = get_employees()

    for emp in employees:

        emp["photo"] = get_last_photo(emp["id"])

    return render_template("dashboard.html", employees=employees)


@app.route("/add_employee", methods=["GET","POST"])
def add_employee():

    if request.method=="POST":

        save_employee(

            request.form["id"],
            request.form["name"],
            request.form["designation"],
            request.form["location"]

        )

        return redirect("/dashboard")

    return render_template("add_employee.html")


@app.route("/attendance/<emp_id>", methods=["GET","POST"])
def attendance(emp_id):

    india = pytz.timezone("Asia/Kolkata")

    employees = get_employees()

    emp_name = emp_id

    for e in employees:

        if e["id"] == emp_id:

            emp_name = e["name"]

    today = datetime.now(india).strftime("%Y-%m-%d")

    record = get_today_record(emp_id,today)

    if request.method=="POST":

        type = request.form["type"]

        img = request.form["image"]

        now = datetime.now(india)

        date = now.strftime("%Y-%m-%d")

        time = now.strftime("%H:%M:%S")

        filename = f"{emp_id}_{type}_{date}_{time}.jpg"

        image_url = upload_image_to_supabase(img, filename)

        if type=="IN":

            save_in(emp_id,emp_name,date,time,image_url)

        else:

            save_out(emp_id,date,time,image_url)

        return redirect(f"/attendance/{emp_id}")

    in_img=""
    out_img=""
    in_time=""
    out_time=""

    if record:

        in_img=record.get("in_image","")
        out_img=record.get("out_image","")
        in_time=record.get("in_time","")
        out_time=record.get("out_time","")

    return render_template(

        "attendance.html",

        emp_id=emp_id,

        in_image=in_img,
        out_image=out_img,

        in_time=in_time,
        out_time=out_time

    )


@app.route("/monthly_report")

def monthly_report():

    month=request.args.get("month")

    url=f"{SUPABASE_URL}/rest/v1/attendance?date=like.{month}%"

    headers={

        "apikey":SUPABASE_KEY,

        "Authorization":f"Bearer {SUPABASE_KEY}"

    }

    r=requests.get(url,headers=headers)

    data=r.json()

    return render_template("monthly_report.html",data=data)


# ---------------- RUN ----------------

if __name__=="__main__":

    port=int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0", port=port)
