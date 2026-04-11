from flask import Flask, render_template, request, redirect
import os, base64, requests
import pytz
from datetime import datetime

app = Flask(__name__)

# ---------------- SUPABASE ----------------

SUPABASE_URL = "https://odbkrbarwhhzfemqfbts.supabase.co"
SUPABASE_KEY = "sb_publishable_9xNlO3TyVXlolLDhjIuuFw_wqdHCTYh"

# upload image to supabase storage
def upload_image_to_supabase(image_data, filename):

    img_data = base64.b64decode(image_data.split(",")[1])

    upload_url = f"{SUPABASE_URL}/storage/v1/object/attendance-images/{filename}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "image/jpeg"
    }

    r = requests.post(upload_url, headers=headers, data=img_data)

    print("IMAGE STATUS:", r.status_code, r.text)

    # public url
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/attendance-images/{filename}"

    return public_url


# save attendance row
def save_attendance(emp_id,name,date,time,image_url):

    url = f"{SUPABASE_URL}/rest/v1/attendance"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "employee_id": emp_id,
        "name": name,
        "date": f"{date} {time}",
        "image_url": image_url
    }

    r = requests.post(url, json=data, headers=headers)

    print("DB STATUS:", r.status_code, r.text)


# get employees
def get_employees():

    url = f"{SUPABASE_URL}/rest/v1/employees?select=*"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    r = requests.get(url, headers=headers)

    return r.json()


# save employee permanently
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

    print("EMP STATUS:", r.status_code, r.text)


# get last image for display
def get_last_image(emp_id):

    url = f"{SUPABASE_URL}/rest/v1/attendance?employee_id=eq.{emp_id}&order=date.desc&limit=1"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    r = requests.get(url, headers=headers)

    data = r.json()

    if len(data) > 0:

        return data[0]["image_url"], data[0]["date"]

    return "", ""


# ---------------- ROUTES ----------------

@app.route("/")
def login():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    employees = get_employees()

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


    if request.method=="POST":

        img = request.form["image"]

        now = datetime.now(india)

        date = now.strftime("%Y-%m-%d")

        time = now.strftime("%H:%M:%S")

        filename = f"{emp_id}_{date}_{time}.jpg"

        image_url = upload_image_to_supabase(img, filename)

        save_attendance(emp_id,emp_name,date,time,image_url)

        return redirect(f"/attendance/{emp_id}")


    last_image, last_time = get_last_image(emp_id)

    return render_template(

        "attendance.html",

        emp_id=emp_id,

        in_time=last_time,

        in_image=last_image,

        out_time="",

        out_image=""

    )


# ---------------- RUN ----------------

if __name__=="__main__":

    port=int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0", port=port)
