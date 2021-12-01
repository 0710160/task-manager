from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from time import time
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


## TaskList table to hold all tasks
class TaskList(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(256))
    date_start = db.Column(db.String, default=datetime.today().strftime('%Y-%m-%d'))
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


#db.create_all()
## Initial population
#init_entry = TaskList(name="test entry", date_start=datetime.today().strftime('%Y-%m-%d'), hours_spent=0, active=False, completed=False)
#db.session.add(init_entry)
#db.session.commit()


@app.route("/")
def home():
    all_tasks = TaskList.query.all()
    return render_template("index.html", all_tasks=all_tasks)

@app.route("/start/<task_id>")
def start(task_id):
    #Starts timer
    task = TaskList.query.get(task_id)
    task.active = True
    task.task_start_time = time()
    db.session.commit()
    all_tasks = TaskList.query.all()
    return render_template("index.html", all_tasks=all_tasks)

@app.route("/end/<task_id>")
def end(task_id):
    #Ends timer and adds hours to db
    task = TaskList.query.get(task_id)
    task.active = False
    task.hours_spent += (time() - task.task_start_time) / 3600
    db.session.commit()
    all_tasks = TaskList.query.all()
    return render_template("index.html", all_tasks=all_tasks)


@app.route("/add")
def add():
    pass


if __name__ == "__main__":
    app.run(debug=True)
