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
import psycopg2

app = Flask(__name__)
ckeditor = CKEditor(app)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'
## TODO: create PDF to text uploader
app.config['UPLOADED_PATH'] = os.path.join(basedir, 'uploads')
app.config['CKEDITOR_HEIGHT'] = 250

## Define folder for image uploads
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
## TODO: work out upload path for Heroku
#UPLOAD_FOLDER = '/home/0710160/ggi/static/uploads/'
ALLOWED_EXTENSIONS = set(['webp', 'png', 'jpg', 'jpeg', 'gif'])

## Connect to DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", 'sqlite:///personal.db')
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return render_template("index.html")


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
        ingredients = [new_recipe_name]
        hr_present = False
        strip_words = ["Ingredients", "INGREDIENTS", "Ingredients:", "INGREDIENTS:",
                       "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
                       "teaspoon", "Teaspoon", "tablespoon", "Tablespoon",
                       "teaspoons", "Teaspoons", "tablespoons", "Tablespoons",
                       "cup", "Cup", "cups", "Cups", "water", "garnish",
                       "large", "small", "medium", "handful", "optional",
                       "(", ")", "/", "lengthwise", "juiced", "overnight",
                       "sliced", "chopped", "dice", "grated", "bruised", "rinsed", "melted", "crushed"]
        for recipe_line in ckeditor_data.splitlines():
            stripped_line = recipe_line.replace("<br />", "").replace("&nbsp;", "").replace("<p>", "").replace("</p", "")
            if "DIRECTION" in stripped_line.upper():
                hr_present = True
                break
            else:
                more_stripped_line = ''.join([i for i in stripped_line if i not in strip_words])
                ingredients.append(more_stripped_line)
        if not hr_present:
            flash("Ensure the word 'Directions' is used after the ingredients section.")
            return render_template("add_recipe.html", form=form)
        else:
            new_recipe = Recipes(title=new_recipe_name,
                                 recipe_body=ckeditor_data,
                                 data_keywords=json.dumps(ingredients))
            db.session.add(new_recipe)
            db.session.commit()
            return redirect(f"/recipe_image/{new_recipe.id}")


@app.route("/recipe_image/<recipe_id>", methods=["GET", "POST"])
@login_required
def recipe_image(recipe_id):
    this_recipe = Recipes.query.get(recipe_id)
    if request.method == 'GET':
        return render_template('recipe_image.html', recipe=this_recipe)
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select a file, browser submits empty part without filename
        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = f'recipe{this_recipe.id}'
            this_recipe.image_url = filename
            db.session.commit()
            #print('upload_image filename: ' + os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('recipes'))


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
@login_required
def edit_recipe(recipe_id):
    form = RecipeForm()
    edit_recipe = Recipes.query.get(recipe_id)
    if request.method == "GET":
        form.title.data = edit_recipe.title
        form.directions.data = edit_recipe.recipe_body
        return render_template("edit_recipe.html", recipe=edit_recipe, form=form)
    else:
        if form.title.data == "":
            pass
        else:
            new_name = form.title.data
            edit_recipe.title = new_name
        if form.directions.data == "":
            pass
        else:
            edit_recipe.info = form.directions.data
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
def taskman():
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
        return redirect(url_for('taskman', tasks=tasks, current_user=current_user))


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
    return redirect(url_for('taskman', tasks=tasks, current_user=current_user))


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
    return redirect(url_for('home', tasks=tasks, current_user=current_user))


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
