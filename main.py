from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from sqlalchemy.orm import relationship
from time import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_ckeditor import CKEditor, CKEditorField, upload_success, upload_fail
import os
import json


#app = Flask(__name__)
app = Flask(__name__, static_folder="frontend/dist/static", template_folder="frontend/dist")
ckeditor = CKEditor(app)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'
## TODO: create PDF to text uploader
## TODO: submit task edit redirects to home; needs to go to tasks
app.config['UPLOADED_PATH'] = '/home/0710160/recipes/static/uploads'
app.config['CKEDITOR_HEIGHT'] = 250

## Connect to DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.sqlite3'
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "lah*(P98&*(g7Wgg1")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


## Flask login manager
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


## WTForms
class TaskForm(FlaskForm):
    name = StringField('Task name:')
    info = CKEditorField('Task info')
    hours = IntegerField('Hours spent:')
    submit = SubmitField()


class RecipeForm(FlaskForm):
    title = StringField('Recipe title:')
    directions = CKEditorField('Directions:')
    submit = SubmitField()


## User table
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(256), unique=True)
    password = db.Column(db.String)
    tasks = relationship("TaskList", backref="user", lazy="dynamic")


## TaskList table to hold all tasks
class TaskList(db.Model):
    __tablename__ = 'tasklist'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(256))
    info = db.Column(db.String)
    date_start = db.Column(db.String, default=datetime.today().strftime('%d-%m-%Y'))
    date_end = db.Column(db.String)
    hours_spent = db.Column(db.Float)
    task_start_time = db.Column(db.Float)
    active = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))


## Recipe table
class Recipes(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(256), nullable=False)
    data_keywords = db.Column(db.String)
    recipe_body = db.Column(db.String)
    date_added = db.Column(db.String, default=datetime.today().strftime('%d-%m-%Y'))
    image_url = db.Column(db.String)


db.create_all()


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/recipes")
def recipes():
    return render_template('recipes.html', recipes=Recipes.query.order_by(Recipes.id.desc()))

@app.route("/recipe/<recipe_id>")
def recipe(recipe_id):
    return render_template("recipe.html", recipe=Recipes.query.get(recipe_id))


@app.route("/add_recipe", methods=["GET", "POST"])
@login_required
def add_recipe():
    form = RecipeForm()
    if request.method == "GET":
        return render_template("add_recipe.html", form=form)
    else:
        new_recipe_name = form.title.data
        ckeditor_data = form.directions.data
        ingredients = []
        hr_present = False
        for i in ckeditor_data.splitlines():
            i = i.strip("'\t'")
            if i != "<hr />":
                ingredients.append(i.replace("<br />", ""))
            else:
                hr_present = True
                break
        if not hr_present:
            flash("Ensure a horizontal line is entered after the ingredients section.")
            return render_template("add_recipe.html", form=form)
        else:
            new_recipe = Recipes(title=new_recipe_name,
                                 recipe_body=ckeditor_data,
                                 data_keywords=json.dumps(ingredients))
            db.session.add(new_recipe)
            db.session.commit()
            return redirect(url_for('recipes'))


@app.route("/delete_recipe/<recipe_id>")
@login_required
def delete_recipe(recipe_id):
    delete_recipe = Recipes.query.get(recipe_id)
    db.session.delete(delete_recipe)
    db.session.commit()
    return redirect(url_for('recipes'))


@app.route("/task_man")
@login_required
def task_man():
    tasks = current_user.tasks.all()
    return render_template("task_man.html", tasks=tasks, current_user=current_user)


@app.route("/start_task/<task_id>")
def start(task_id):
    # Starts timer
    task = TaskList.query.get(task_id)
    task.active = True
    task.task_start_time = time()
    db.session.commit()
    return redirect(request.referrer)


@app.route("/end_task/<task_id>")
def end(task_id):
    # Ends timer and adds hours to db
    task = TaskList.query.get(task_id)
    task.active = False
    time_in_hours = (time() - task.task_start_time) / 3600
    if task.hours_spent is None:
        task.hours_spent = time_in_hours
    else:
        task.hours_spent = float(time_in_hours + task.hours_spent)
    db.session.commit()
    return redirect(request.referrer)


@app.route("/add_task", methods=["GET", "POST"])
@login_required
def add():
    form = TaskForm()
    if request.method == "GET":
        return render_template("add_task.html", form=form)
    else:
        new_task_name = form.name.data
        ckeditor_data = form.info.data
        new_task = TaskList(name=new_task_name, info=ckeditor_data, user=current_user)
        db.session.add(new_task)
        db.session.commit()
        tasks = current_user.tasks.all()
        return redirect(url_for('task_man', tasks=tasks, current_user=current_user))


@app.route("/edit_task/<task_id>", methods=["GET", "POST"])
@login_required
def edit(task_id):
    form = TaskForm()
    edit_task = TaskList.query.get(task_id)
    if request.method == "GET":
        form.info.data = edit_task.info
        return render_template("edit_task.html", task=edit_task, form=form)
    else:
        if form.name.data == "":
            pass
        else:
            new_name = form.name.data
            edit_task.name = new_name
        try:
            new_hours = int(form.hours.data)
            edit_task.hours_spent = new_hours
        except TypeError:
            pass
        if form.info.data == "":
            pass
        else:
            edit_task.info = form.info.data
    db.session.commit()
    tasks = current_user.tasks.all()
    return redirect(url_for('task_man', tasks=tasks, current_user=current_user))


@app.route("/complete_task/<task_id>")
def complete(task_id):
    edit_task = TaskList.query.get(task_id)
    edit_task.completed = True
    edit_task.date_end = datetime.today().strftime('%d-%m-%Y')
    db.session.commit()
    return redirect(request.referrer)


@app.route("/delete_task/<task_id>")
def delete(task_id):
    delete_task = TaskList.query.get(task_id)
    db.session.delete(delete_task)
    db.session.commit()
    tasks = current_user.tasks.all()
    return redirect(url_for('task_man', tasks=tasks, current_user=current_user))


## CKEditor handling
@app.route('/files/<filename>')
def uploaded_files(filename):
    path = app.config['UPLOADED_PATH']
    return send_from_directory(path, filename)


@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('upload')
    extension = f.filename.split('.')[-1].lower()
    if extension not in ['jpg', 'gif', 'png', 'jpeg']:
        return upload_fail(message='Images only!')
    f.save(os.path.join(app.config['UPLOADED_PATH'], f.filename))
    url = url_for('uploaded_files', filename=f.filename)
    return upload_success(url, filename=f.filename)


## User handling functions
@app.route("/fZfI@^0lXOfRv2Ks&RI(1Ov4", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template('register.html')
    else:
        password = generate_password_hash(
            request.form["password"],
            method='pbkdf2:sha256',
            salt_length=8
        )
        email = request.form["email"]
        new_user = User(email=email, password=password)
        if User.query.filter_by(email=email).first():
            flash("This email address is already in use.")
            return redirect(url_for('login'))
        else:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            tasks = current_user.tasks.all()
            return redirect(url_for('home', tasks=tasks, current_user=current_user))


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.method == "POST":
        email = request.form["email"]
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            flash("Account does not exist in database. Please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, request.form["password"]):
            flash("Incorrect password. Please try again.")
            return redirect(url_for('login'))
        else:
            login_user(user, remember=True)
            tasks = current_user.tasks.all()
            return redirect(url_for('home', tasks=tasks, current_user=current_user))


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))


## Error handling
@app.errorhandler(401)
def auth_401(error):
    flash("You need to be logged in to do that.")
    return render_template("login.html"), 401


@app.errorhandler(500)
def special_exception_handler(error):
    return "Database error."


if __name__ == "__main__":
    app.run(debug=True)
