from flask import Flask, render_template, request, redirect, send_file
import sqlite3
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import PatternFill

app = Flask(__name__)

def db():
    return sqlite3.connect("database.db")

# create tables first time
def create_tables():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees(
        id TEXT,
        name TEXT,
        designation TEXT,
        location TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        emp_id TEXT,
        date TEXT,
        in_time TEXT,
        out_time TEXT,
        latitude TEXT,
        longitude TEXT
    )
    """)

    con.commit()

create_tables()

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM employees")
    data = cur.fetchall()
    return render_template("dashboard.html", employees=data)

@app.route("/add_employee", methods=["GET","POST"])
def add_employee():

    if request.method=="POST":

        emp_id = request.form["id"]
        name = request.form["name"]
        desig = request.form["designation"]
        loc = request.form["location"]

        con = db()
        cur = con.cursor()

        cur.execute("INSERT INTO employees VALUES(?,?,?,?)",
                    (emp_id,name,desig,loc))

        con.commit()

        return redirect("/dashboard")

    return render_template("add_employee.html")

@app.route("/attendance/<emp_id>", methods=["GET","POST"])
def attendance(emp_id):

    if request.method=="POST":

        lat = request.form["lat"]
        lon = request.form["lon"]

        now = datetime.now()

        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M")

        con = db()
        cur = con.cursor()

        cur.execute("""
        SELECT * FROM attendance
        WHERE emp_id=? AND date=?
        """,(emp_id,date))

        row = cur.fetchone()

        if row is None:

            cur.execute("""
            INSERT INTO attendance
            VALUES(?,?,?,?,?,?)
            """,(emp_id,date,time,"",lat,lon))

        else:

            cur.execute("""
            UPDATE attendance
            SET out_time=?
            WHERE emp_id=? AND date=?
            """,(time,emp_id,date))

        con.commit()

        return redirect("/dashboard")

    return render_template("attendance.html", emp_id=emp_id)

@app.route("/excel")

def excel():

    con=db()
    cur=con.cursor()

    cur.execute("SELECT * FROM employees")
    employees=cur.fetchall()

    wb=Workbook()
    ws=wb.active

    ws.append(["Employee","Date","Status"])

    green=PatternFill(start_color="00FF00",fill_type="solid")
    yellow=PatternFill(start_color="FFFF00",fill_type="solid")
    red=PatternFill(start_color="FF0000",fill_type="solid")

    for e in employees:

        cur.execute("""
        SELECT in_time,out_time,date
        FROM attendance
        WHERE emp_id=?
        """,(e[0],))

        rows=cur.fetchall()

        for r in rows:

            if r[1]=="":
                status="A"
                color=red

            else:

                t1=datetime.strptime(r[0],"%H:%M")
                t2=datetime.strptime(r[1],"%H:%M")

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

            ws.append([e[1],r[2],status])

            ws.cell(ws.max_row,3).fill=color

    file="attendance.xlsx"
    wb.save(file)

    return send_file(file,as_attachment=True)

import os

port = int(os.environ.get("PORT", 5000))

app.run(host="0.0.0.0", port=port)
