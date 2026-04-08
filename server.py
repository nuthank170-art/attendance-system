from flask import Flask, render_template, request, redirect, send_file
import sqlite3, os, base64
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import PatternFill

app = Flask(__name__)

def db():
    return sqlite3.connect("database.db")

def create_tables():
    con=db()
    cur=con.cursor()

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
    out_time TEXT)
    """)

    con.commit()

create_tables()

def save_image(data,name):
    if data=="":
        return
    img=data.split(",")[1]
    with open("static/"+name,"wb") as f:
        f.write(base64.b64decode(img))

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

        cur.execute("insert into employees values(?,?,?,?)",
        (
        request.form["id"],
        request.form["name"],
        request.form["designation"],
        request.form["location"]
        ))

        con.commit()

        return redirect("/dashboard")

    return render_template("add_employee.html")

@app.route("/attendance/<emp_id>", methods=["GET","POST"])
def attendance(emp_id):

    if request.method == "POST":

        type = request.form["type"]
        img = request.form["image"]

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        con = db()
        cur = con.cursor()

        cur.execute(
        "SELECT * FROM attendance WHERE emp_id=? AND date=?",
        (emp_id,date)
        )

        row = cur.fetchone()

        if type == "IN":

            cur.execute(
            "INSERT INTO attendance VALUES (?,?,?,?)",
            (emp_id,date,time,"")
            )

            save_image(img,f"{emp_id}_in.jpg")

        else:

            cur.execute(
            """
            UPDATE attendance
            SET out_time=?
            WHERE emp_id=? AND date=?
            """,
            (time,emp_id,date)
            )

            save_image(img,f"{emp_id}_out.jpg")

        con.commit()

        return redirect(f"/attendance/{emp_id}")


    # show time on page
    con = db()
    cur = con.cursor()

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

    in_time = ""
    out_time = ""

    if row:
        in_time = row[0]
        out_time = row[1]

    return render_template(
    "attendance.html",
    emp_id=emp_id,
    in_time=in_time,
    out_time=out_time
    )


@app.route("/report",methods=["GET","POST"])
def report():

    data=[]

    if request.method=="POST":

        f=request.form["from"]
        t=request.form["to"]

        con=db()
        cur=con.cursor()

        cur.execute("""
        select * from attendance
        where date between ? and ?
        """,(f,t))

        data=cur.fetchall()

    return render_template("report.html",data=data)

@app.route("/excel")
def excel():

    con=db()
    cur=con.cursor()

    cur.execute("select * from attendance")
    rows=cur.fetchall()

    wb=Workbook()
    ws=wb.active

    ws.append(["Emp","Date","Status"])

    green=PatternFill(start_color="00FF00",fill_type="solid")
    yellow=PatternFill(start_color="FFFF00",fill_type="solid")
    red=PatternFill(start_color="FF0000",fill_type="solid")

    for r in rows:

        if r[3]=="":
            status="A"
            color=red

        else:

            t1=datetime.strptime(r[2],"%H:%M:%S")
            t2=datetime.strptime(r[3],"%H:%M:%S")

            hrs=(t2-t1).seconds/3600

            if hrs>=8:
                status="P"
                color=green
            elif hrs>=4:
                status="PH"
                color=yellow
            else:
                status="A"
                color=red

        ws.append([r[0],r[1],status])
        ws.cell(ws.max_row,3).fill=color

    wb.save("report.xlsx")

    return send_file("report.xlsx",as_attachment=True)

@app.route("/delete_employee/<id>")
def delete_employee(id):

    con=db()
    cur=con.cursor()

    cur.execute("delete from employees where id=?",(id,))
    con.commit()

    return redirect("/dashboard")


@app.route("/edit_employee/<id>",methods=["GET","POST"])
def edit_employee(id):

    con=db()
    cur=con.cursor()

    if request.method=="POST":

        cur.execute("""
        update employees
        set name=?,designation=?,location=?
        where id=?
        """,
        (
        request.form["name"],
        request.form["designation"],
        request.form["location"],
        id
        ))

        con.commit()

        return redirect("/dashboard")

    cur.execute("select * from employees where id=?",(id,))
    emp=cur.fetchone()

    return render_template("edit_employee.html",emp=emp)
    
if __name__=="__main__":

    port=int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0",port=port)
