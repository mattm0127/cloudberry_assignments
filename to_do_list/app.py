import os

import sqlite3
from datetime import datetime

from flask import Flask, render_template, redirect, request, flash, url_for

app = Flask(__name__)
app.secret_key = "pick something secure"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'todo.db')


class DatabaseConnection:

    def __init__(self, database, app):
        self.database = database
        self.app = app

    def _process_date(self, task_tuple):
        if task_tuple[3]:
            return datetime.strptime(task_tuple[3], "%Y-%m-%d").strftime("%d-%b-%Y")
        else:
            return "TBD"

    def _process_tuples(self, task_tuples):
        tasks = []
        for task_tuple in task_tuples:
            due_date = self._process_date(task_tuple)
            task = {
                "task_id": task_tuple[0],
                "task_list_id": task_tuple[1],
                "task": task_tuple[2],
                "due_date": due_date,
                "complete": task_tuple[4],
                "task_list_name": task_tuple[6]

            }
            tasks.append(task)
        print(tasks)
        return tasks

    def get_db(self):
        conn = sqlite3.connect(self.database)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_task_lists_table(self):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL)
                    """)
        db.commit()
        db.close()

    def create_tasks_table(self):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_list_id INTEGER,
                    task TEXT NOT NULL,
                    due_date DATETIME,
                    complete BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (task_list_id) 
                        REFERENCES task_lists(id) 
                        ON DELETE CASCADE)
                    """)
        db.commit()
        db.close()

    def initialize_database(self):
        self.create_task_lists_table()
        self.create_tasks_table()

    def home_get(self):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM task_lists ")
        task_lists = cursor.fetchall()
        db.close()
        return [{'id': task_list[0], 'name':task_list[1]} for task_list in task_lists]
    
    def task_list_get(self, name):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("""
                       SELECT * FROM tasks
                            JOIN task_lists ON tasks.task_list_id = task_lists.id
                            WHERE task_lists.name = ?
                            ORDER BY due_date
                       """, (name,))
        task_tuples = cursor.fetchall()
        db.close()
        return self._process_tuples(task_tuples)

    def add_task_list_post(self, task_list):
        db = self.get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO task_lists (name) VALUES (?)", (task_list,))
            db.commit()
        except Exception:
            raise Exception
        finally:
            db.close()

    def add_task_post(self, task_list, task, due_date):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO tasks (task_list_id, task, due_date)
              SELECT id, ?, ?
              FROM task_lists
              WHERE name = ?""",
            (task, due_date, task_list)
        )
        db.commit()
        db.close()

    def edit_task_get(self, id):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT task, due_date FROM tasks WHERE ID = ?",
            (id,),
        )
        task, due_date = cursor.fetchone()
        db.close()
        return task, due_date

    def edit_task_post(self, id, task, due_date):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE tasks SET task = ?, due_date = ? WHERE id = ?",
            (task, due_date, id),
        )
        db.commit()
        db.close()

    def complete_task_post(self, id):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute(
            """UPDATE tasks 
                    SET complete = CASE
                        WHEN complete = 1 THEN 0 ELSE 1
                        END
                    WHERE id = ?""",
            (id,),
        )
        db.commit()
        cursor.execute("SELECT complete FROM tasks WHERE id = ?", (id,))
        complete = cursor.fetchone()[0]
        db.close()
        return complete

    def delete_task_post(self, id):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM tasks WHERE ID = ?", (id,))
        db.commit()
        db.close()

    def clear_tasks_post(self, list_name):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("""
                       DELETE FROM tasks WHERE task_list_id = (
                            SELECT id FROM task_lists
                                WHERE name = ?)
                       """,
                       (list_name,)
                       )
        db.commit()
        db.close()

    def delete_task_list_post(self, list_name):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM task_lists WHERE name = ?", (list_name,))
        db.commit()
        db.close()

db_connect = DatabaseConnection(DATABASE, app)
db_connect.initialize_database() # For Python Anywhere


@app.route("/")
def home():
    task_lists = db_connect.home_get()
    return render_template("index.html", task_lists=task_lists)

@app.route("/add_list", methods=["POST"])
def add_task_list():
    list_name = request.form.get("task_list", None)
    if list_name:
        try:
            db_connect.add_task_list_post(list_name)
            flash("New Task List Created.", category='message')
        except Exception:
            flash("List Already Exists.", category='message')
    return redirect(url_for('home'))

@app.route("/<list_name>/")
def task_list(list_name):
    tasks = db_connect.task_list_get(list_name)
    return render_template('task_list.html', list_name=list_name, tasks = tasks)

@app.route("/<list_name>/add", methods=["POST"])
def add_task(list_name):
    task = request.form.get("task")
    due_date = request.form.get("due_date", None)
    if task:
        db_connect.add_task_post(list_name, task, due_date)
        flash("New task Added.", category="message")
    return redirect(url_for("task_list", list_name=list_name))

@app.route("/<list_name>/edit/<int:id>", methods=["GET", "POST"])
def edit_task(list_name, id):
    if request.method == "POST":
        task = request.form.get("task")
        due_date = request.form.get("due_date")
        if task:
            db_connect.edit_task_post(id, task, due_date) 
            flash("Task Edited.", category="message")
        return redirect(url_for("task_list", list_name=list_name))
    task, due_date = db_connect.edit_task_get(id)
    return render_template(
        "edit_task.html", 
        id=id, 
        task=task, 
        due_date=due_date, 
        list_name=list_name)

@app.route("/<list_name>/complete/<int:id>", methods=["POST"])
def complete_task(list_name, id):
    if db_connect.complete_task_post(id):
        flash("Task Completed.", category="message")
    return redirect(url_for("task_list", list_name=list_name))

@app.route("/<list_name>/delete/<int:id>", methods=["GET", "POST"])
def delete_task(list_name, id):
    if request.method == "POST":
        db_connect.delete_task_post(id)
        flash("Task Deleted.", category="message")
        return redirect(url_for("task_list", list_name=list_name))
    return render_template('confirm_delete.html', list_name=list_name, id=id, delete_type='task')

@app.route("/<list_name>/clear", methods=["GET", "POST"])
def clear_tasks(list_name):
    if request.method == "POST":
        db_connect.clear_tasks_post(list_name)
        flash("Task List Cleared.", category="message")
        return redirect(url_for("task_list", list_name=list_name))
    return render_template("confirm_delete.html", list_name=list_name, id=id, delete_type='clear')

@app.route("/<list_name>/delete", methods=["GET", "POST"])
def delete_task_list(list_name):
    if request.method == "POST":
        db_connect.delete_task_list_post(list_name)
        flash("Task List Deleted.", category="message")
        return redirect(url_for('home'))
    return render_template('confirm_delete.html', list_name=list_name, delete_type='task_list')

if __name__ == "__main__":
    db_connect.initialize_database()
    app.run(debug=True)
