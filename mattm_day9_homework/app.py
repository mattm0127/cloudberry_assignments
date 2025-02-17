import sqlite3
from datetime import datetime

from flask import Flask, render_template, redirect, request, flash

app = Flask(__name__)
app.secret_key = "pick something secure"
DATABASE = "todo.db"


class DatabaseConnection:
    def __init__(self, database, app):
        self.database = database
        self.app = app

    def _process_date(self, task_tuple):
        if task_tuple[2]:
            return datetime.strptime(task_tuple[2], "%Y-%m-%d").strftime("%d-%b-%Y")
        else:
            return "TBD"

    def _process_tuples(self, task_tuples):
        tasks = []
        for task_tuple in task_tuples:
            due_date = self._process_date(task_tuple)
            task = {
                "id": task_tuple[0],
                "task": task_tuple[1],
                "due_date": due_date,
                "complete": task_tuple[3],
            }
            tasks.append(task)
        return tasks

    def get_db(self):
        return sqlite3.connect(self.database)

    def create_table(self):
        with self.app.app_context():
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task TEXT NOT NULL,
                        due_date DATETIME,
                        complete BOOLEAN DEFAULT FALSE)
                        """)
            db.commit()
            db.close()

    def home_get(self):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("""
                       SELECT * FROM tasks 
                            ORDER BY due_date
                       """)
        task_tuples = cursor.fetchall()
        db.close()
        return self._process_tuples(task_tuples)

    def add_task_post(self, task, due_date):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO tasks (task, due_date) VALUES (?,?)",
            (task, due_date),
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

    def clear_tasks_post(self):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("DROP TABLE tasks")
        db.commit()
        db.close()
        self.create_table()


db_connect = DatabaseConnection(DATABASE, app)
db_connect.create_table() # For Python Anywhere


@app.route("/")
def home():
    tasks = db_connect.home_get()
    return render_template("index.html", tasks=tasks)


@app.route("/add", methods=["POST"])
def add_task():
    task = request.form.get("task")
    due_date = request.form.get("due_date", None)
    if task:
        db_connect.add_task_post(task, due_date)
        flash("New task Added.", category="message")
    return redirect("/")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_task(id):
    if request.method == "POST":
        task = request.form.get("task")
        due_date = request.form.get("due_date")
        if task:
            db_connect.edit_task_post(id, task, due_date)
            flash("Task Edited.", category="message")
        return redirect("/")
    task, due_date = db_connect.edit_task_get(id)
    return render_template("edit_task.html", id=id, task=task, due_date=due_date)


@app.route("/complete/<int:id>", methods=["POST"])
def complete_task(id):
    if db_connect.complete_task_post(id):
        flash("Task Completed.", category="message")
    return redirect("/")


@app.route("/delete/<int:id>", methods=["POST"])
def delete_task(id):
    db_connect.delete_task_post(id)
    flash("Task Deleted.", category="message")
    return redirect("/")


@app.route("/clear", methods=["POST"])
def clear_tasks():
    db_connect.clear_tasks_post()
    flash("Task List Cleared.", category="message")
    return redirect("/")


if __name__ == "__main__":
    db_connect.create_table()
    app.run(debug=True)
