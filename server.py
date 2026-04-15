from flask import Flask, render_template, request, redirect
import os, base64, requests
import pytz
from datetime import datetime

app = Flask(__name__)

# ---------------- SUPABASE ----------------

SUPABASE_URL = "https://odbkrbarwhhzfemqfbts.supabase.co"
SUPABASE_KEY = "sb_publishable_9xNlO3TyVXlolLDhjIuuFw_wqdHCTYh"


# ---------------- WHATSAPP ----------------

def send_whatsapp_group(name,punch_type,date,time):

    instance_id = "instance170176"

    token = "1s7j5er6qdeigt2m"

    group_id = "120363424682689340@g.us"

    message = f"{name}\n{punch_type}\n{date}\n{time}"

    url = f"https://api.ultramsg.com/{instance_id}/messages/chat"

    data = {

        "token": token,

        "to": group_id,

        "body": message

    }

    requests.post(url, data=data)


# upload image to supabase storage
def upload_image_to_supabase(image_data, filename):

    img_data = base64.b64decode(image_data.split(",")[1])

    upload_url = f"{SUPABASE_URL}/storage/v1/object/attendance-images/{filename}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/octet-stream"
    }

    r = requests.post(upload_url, headers=headers, data=img_data)

    print("IMAGE STATUS:", r.status_code)
    print(r.text)

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/attendance-images/{filename}"

    return public_url


# save attendance row
def save_attendance(emp_id,name,date,time,image_url,punch_type):

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    if punch_type=="IN":

        data = {
            "employee_id": emp_id,
            "name": name,
            "date": date,
            "in_time": time,
            "in_image": image_url
        }

        r = requests.post(

            f"{SUPABASE_URL}/rest/v1/attendance",

            json=data,

            headers=headers

        )

        print("IN SAVED:", r.status_code, r.text)

    else:

        r = requests.patch(

            f"{SUPABASE_URL}/rest/v1/attendance?employee_id=eq.{emp_id}&date=eq.{date}",

            json={
                "out_time": time,
                "out_image": image_url
            },

            headers=headers

        )

        print("OUT SAVED:", r.status_code, r.text)


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


# get last images
def get_last_images(emp_id):

    url = f"{SUPABASE_URL}/rest/v1/attendance?employee_id=eq.{emp_id}&order=date.desc&limit=1"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    r = requests.get(url, headers=headers)

    data = r.json()

    if len(data) > 0:

        return (

            data[0].get("in_image",""),
            data[0].get("out_image",""),
            data[0].get("in_time",""),
            data[0].get("out_time","")

        )

    return "","","",""


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

        punch_type = request.form["type"]

        img = request.form["image"]

        now = datetime.now(india)

        date = now.strftime("%Y-%m-%d")

        time = now.strftime("%H:%M:%S")

        filename = f"{emp_id}_{punch_type}_{date}_{time}.jpg"

        image_url = upload_image_to_supabase(img, filename)

        save_attendance(

            emp_id,
            emp_name,
            date,
            time,
            image_url,
            punch_type

        )

        # SEND WHATSAPP MESSAGE
        send_whatsapp_group(emp_name,punch_type,date,time)

        return redirect(f"/attendance/{emp_id}")


    headers = {

        "apikey": SUPABASE_KEY,

        "Authorization": f"Bearer {SUPABASE_KEY}"

    }

    today = datetime.now(india).strftime("%Y-%m-%d")

    r = requests.get(

        f"{SUPABASE_URL}/rest/v1/attendance?employee_id=eq.{emp_id}&date=eq.{today}",

        headers=headers

    )

    data = r.json()

    in_img=""
    out_img=""
    in_time=""
    out_time=""

    if len(data)>0:

        in_img = data[0].get("in_image","")
        out_img = data[0].get("out_image","")

        in_time = data[0].get("in_time","")
        out_time = data[0].get("out_time","")


    return render_template(

        "attendance.html",

        emp_id=emp_id,

        in_image=in_img,
        out_image=out_img,

        in_time=in_time,
        out_time=out_time

    )


# monthly photo report
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
