import os

import sqlite3
from datetime import datetime

from flask import Flask, render_template, redirect, request, flash, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "pick something secure"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = 'sqlite:///' + os.path.join(BASE_DIR, 'todo.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE
app.config['SQLALCHEMY_TRACK_NOTIFICATIONS'] = False
db = SQLAlchemy(app)

class Users(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(20), nullable=False)

class TaskLists(db.Model):
    __tablename__ = 'task_lists'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False, unique=True)
    tasks = db.relationship('Tasks', back_populates="task_list", cascade="all, delete")

class Tasks(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_list_id = db.Column(db.Integer, db.ForeignKey('task_lists.id'), nullable=False)
    task = db.Column(db.String(20), nullable=False)
    due_date = db.Column(db.String, default='TBD')
    complete = db.Column(db.Boolean, default=False)
    date_entered = db.Column(db.DateTime, default=db.func.now())
    task_list = db.relationship('TaskLists', back_populates='tasks')

class DatabaseClient:
    
    def __init__(self, db):
        self.db = db

    def initialize_database(self):
        with app.app_context():
            self.db.create_all()

    def add_user(self, username, password):
        try:
            new_user = Users(username=username, password=password)
            self.db.session.add(new_user)
            self.db.session.commit()
            return True
        except Exception:
            return False
    
    def valiate_user(self, username, password):
        try:
            user = Users.query.filter(Users.username==username).first()
            if user.password == password:
                return True
            else:
                return False
        except Exception:
            return False

        
    def home_get(self):
        task_lists = TaskLists.query.all()
        return task_lists
    
    def task_list_get(self, name, task_filter):
        if task_filter == 'all':
            tasks = Tasks.query.join(TaskLists).filter(TaskLists.name == name).all()
        elif task_filter == 'complete':
            tasks = Tasks.query.join(TaskLists).filter(TaskLists.name == name, Tasks.complete == True).all()
        elif task_filter == 'incomplete':
            tasks = Tasks.query.join(TaskLists).filter(TaskLists.name == name, Tasks.complete == False).all()
        return tasks

    def add_task_list_post(self, task_list):
        try:
            new_task_list = TaskLists(name=task_list)
            self.db.session.add(new_task_list)
            self.db.session.commit()
        except Exception:
            raise Exception

    def add_task_post(self, task_list, task, due_date):
        task_list_id = TaskLists.query.filter(TaskLists.name == task_list)[0]
        new_task = Tasks(task_list_id = task_list_id.id, task=task, due_date=due_date)
        self.db.session.add(new_task)
        self.db.session.commit()

    def edit_task_get(self, id):
        task = Tasks.query.get(id)
        return task

    def edit_task_post(self, id, task, due_date):
        update_task = Tasks.query.get(id)
        update_task.task = task
        update_task.due_date = due_date
        self.db.session.commit()

    def complete_task_post(self, id):
        update_task = Tasks.query.get(id)
        update_task.complete = True if update_task.complete is False else False
        self.db.session.commit()
        return update_task.complete

    def delete_task_post(self, id):
        delete_task = Tasks.query.get(id)
        self.db.session.delete(delete_task)
        self.db.session.commit()

    def clear_tasks_post(self, list_name):
        task_list_id = TaskLists.query.filter(TaskLists.name==list_name)[0].id
        tasks_deleted = Tasks.query.filter(Tasks.task_list_id==task_list_id).delete()
        self.db.session.commit()

    def delete_task_list_post(self, list_name):
        task_list = TaskLists.query.filter(TaskLists.name==list_name)[0]
        self.db.session.delete(task_list)
        self.db.session.commit()


#db_client.initialize_database() # For Python Anywhere
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        if db_client.valiate_user(username, password):
            session['username'] = username
            return redirect(url_for("home"))
        return render_template('login.html', error='Username or Password Incorrect. Try Again.')
    return render_template('login.html')

@app.route('/login/register', methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('register.html', error='Please Enter a Username and Password.')
        if db_client.add_user(username, password):
            session['username'] = username
            return redirect(url_for("home"))
        return render_template('register.html', error='Username already taken.')
    return render_template('register.html')

@app.route("/logout")
def logout():
    session.pop('username')
    return redirect(url_for('login'))

@app.route("/")
def home():
    if not session.get('username'):
        return redirect(url_for('login'))
    task_lists = db_client.home_get()
    return render_template("index.html", task_lists=task_lists)

@app.route("/add_list", methods=["POST"])
def add_task_list():
    list_name = request.form.get("task_list", None)
    if list_name:
        try:
            db_client.add_task_list_post(list_name)
            flash("New Task List Created.", category='message')
        except Exception:
            flash("List Already Exists.", category='message')
    return redirect(url_for('home'))

@app.route("/<list_name>/<task_filter>")
def task_list(list_name, task_filter):
    tasks = db_client.task_list_get(list_name, task_filter)
    return render_template('task_list.html', list_name=list_name, tasks = tasks)

@app.route("/<list_name>/add", methods=["POST"])
def add_task(list_name):
    task = request.form.get("task")
    due_date = request.form.get("due_date", None)
    if task:
        db_client.add_task_post(list_name, task, due_date)
        flash("New task Added.", category="message")
    return redirect(url_for("task_list", list_name=list_name, task_filter='all'))

@app.route("/<list_name>/edit/<int:id>", methods=["GET", "POST"])
def edit_task(list_name, id):
    if request.method == "POST":
        task = request.form.get("task")
        due_date = request.form.get("due_date")
        if task:
            db_client.edit_task_post(id, task, due_date) 
            flash("Task Edited.", category="message")
        return redirect(url_for("task_list", list_name=list_name, task_filter='all'))
    task = db_client.edit_task_get(id)
    return render_template(
        "edit_task.html", 
        task=task,
        list_name=list_name)

@app.route("/<list_name>/complete/<int:id>", methods=["POST"])
def complete_task(list_name, id):
    if db_client.complete_task_post(id):
        flash("Task Completed.", category="message")
    return redirect(url_for("task_list", list_name=list_name, task_filter='all'))

@app.route("/<list_name>/delete/<int:id>", methods=["GET", "POST"])
def delete_task(list_name, id):
    if not session.get('username'):
        flash("You must be logged in to edit.", category="message")
        return redirect(url_for("task_list", list_name=list_name, task_filter='all'))
    if request.method == "POST":
        db_client.delete_task_post(id)
        flash("Task Deleted.", category="message")
        return redirect(url_for("task_list", list_name=list_name, task_filter='all'))
    return render_template('confirm_delete.html', list_name=list_name, id=id, delete_type='task')

@app.route("/<list_name>/clear", methods=["GET", "POST"])
def clear_tasks(list_name):
    if not session.get('username'):
        flash("You must be logged in to edit.", category="message")
        return redirect(url_for("task_list", list_name=list_name, task_filter='all'))
    if request.method == "POST":
        db_client.clear_tasks_post(list_name)
        flash("Task List Cleared.", category="message")
        return redirect(url_for("task_list", list_name=list_name, task_filter='all'))
    return render_template("confirm_delete.html", list_name=list_name, delete_type='clear')

@app.route("/<list_name>/delete", methods=["GET", "POST"])
def delete_task_list(list_name):
    if not session.get('username'):
        flash("You must be logged in to edit.", category="message")
        return redirect(url_for("task_list", list_name=list_name, task_filter='all'))
    if request.method == "POST":
        db_client.delete_task_list_post(list_name)
        flash("Task List Deleted.", category="message")
        return redirect(url_for('home'))
    return render_template('confirm_delete.html', list_name=list_name, delete_type='task_list')

if __name__ == "__main__":
    db_client = DatabaseClient(db)
    db_client.initialize_database()
    app.run(debug=True)
