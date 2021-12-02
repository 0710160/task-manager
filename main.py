from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from time import time
from datetime import datetime
import os
import psycopg2

##TODO: add footer with Snaptank info just for shigs
##TODO: add media query for mobile use

app = Flask(__name__)

## Connect to DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", 'sqlite:///timer.db')
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


## TaskList table to hold all tasks
class TaskList(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(256))
    date_start = db.Column(db.String, default=datetime.today().strftime('%d-%m-%Y'))
    date_end = db.Column(db.String)
    hours_spent = db.Column(db.Float)
    task_start_time = db.Column(db.Float)
    active = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)


## Notes table to hold to-dos and notes associated with each task
class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer)
    note = db.Column(db.String)
    done = db.Column(db.Boolean, default=False)


db.create_all()


@app.route("/")
def home():
    active_tasks = db.session.query(TaskList).filter_by(completed=False).all()
    completed_tasks = db.session.query(TaskList).filter_by(completed=True).all()
    return render_template("index.html", active_tasks=active_tasks, completed_tasks=completed_tasks)


@app.route("/start/<task_id>")
def start(task_id):
    #Starts timer
    task = TaskList.query.get(task_id)
    task.active = True
    task.task_start_time = time()
    db.session.commit()
    active_tasks = db.session.query(TaskList).filter_by(completed=False).all()
    completed_tasks = db.session.query(TaskList).filter_by(completed=True).all()
    return redirect(url_for('home', active_tasks=active_tasks, completed_tasks=completed_tasks))


@app.route("/end/<task_id>")
def end(task_id):
    #Ends timer and adds hours to db
    task = TaskList.query.get(task_id)
    task.active = False
    time_in_hours = (time() - task.task_start_time) / 3600
    if task.hours_spent is None:
        task.hours_spent = time_in_hours
    else:
        task.hours_spent = float(time_in_hours + task.hours_spent)
    db.session.commit()
    active_tasks = db.session.query(TaskList).filter_by(completed=False).all()
    completed_tasks = db.session.query(TaskList).filter_by(completed=True).all()
    return redirect(url_for('home', active_tasks=active_tasks, completed_tasks=completed_tasks))


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "GET":
        return render_template("add.html")
    else:
        new_task_name = request.form["name"]
        new_task = TaskList(name=new_task_name)
        db.session.add(new_task)
        #get hold of new task after adding it to db so assign task_id
        get_new_task = db.session.query(TaskList).filter_by(name=new_task_name).first()
        new_task_notes = request.form["note"]
        new_note = Notes(note=new_task_notes, task_id=get_new_task.id)
        db.session.add(new_note)
        db.session.commit()
        active_tasks = db.session.query(TaskList).filter_by(completed=False).all()
        completed_tasks = db.session.query(TaskList).filter_by(completed=True).all()
        return redirect(url_for('home', active_tasks=active_tasks, completed_tasks=completed_tasks))


@app.route("/edit/<task_id>", methods=["GET", "POST"])
def edit(task_id):
    edit_task = TaskList.query.get(task_id)
    notes = db.session.query(Notes).filter_by(task_id=edit_task.id).all()
    if request.method == "GET":
        return render_template("edit.html", task=edit_task, notes=notes)
    else:
        if request.form["name"] == "":
            pass
        else:
            new_name = request.form["name"]
            edit_task.name = new_name
        if request.form["hours"] == "":
            pass
        else:
            new_hours = request.form["hours"]
            edit_task.hours_spent = new_hours
        if request.form["notes"] == "":
            pass
        else:
            note = request.form["notes"]
            new_note = Notes(task_id=task_id, note=note)
            db.session.add(new_note)
    db.session.commit()
    active_tasks = db.session.query(TaskList).filter_by(completed=False).all()
    completed_tasks = db.session.query(TaskList).filter_by(completed=True).all()
    return redirect(url_for('home', active_tasks=active_tasks, completed_tasks=completed_tasks))


@app.route("/complete/<task_id>")
def complete(task_id):
    edit_task = TaskList.query.get(task_id)
    edit_task.completed = True
    edit_task.date_end = datetime.today().strftime('%d-%m-%Y')
    db.session.commit()
    active_tasks = db.session.query(TaskList).filter_by(completed=False).all()
    completed_tasks = db.session.query(TaskList).filter_by(completed=True).all()
    return redirect(url_for('home', active_tasks=active_tasks, completed_tasks=completed_tasks))


@app.route("/delete/<task_id>")
def delete(task_id):
    delete_task = TaskList.query.get(task_id)
    db.session.delete(delete_task)
    delete_notes = db.session.query(Notes).filter_by(task_id=delete_task.id).all()
    db.session.delete(delete_notes)
    db.session.commit()
    active_tasks = db.session.query(TaskList).filter_by(completed=False).all()
    completed_tasks = db.session.query(TaskList).filter_by(completed=True).all()
    return redirect(url_for('home', active_tasks=active_tasks, completed_tasks=completed_tasks))


if __name__ == "__main__":
    app.run(debug=True)
