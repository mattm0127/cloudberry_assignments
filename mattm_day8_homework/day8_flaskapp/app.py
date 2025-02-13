from flask import Flask, render_template, redirect, url_for, request
import datetime
app = Flask(__name__)

# github link - https://github.com/mattm0127
# CSS needs work
feedback_dict = {}

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get('name')
        fact = request.form.get('fact')
        return render_template('about.html', name=name, fact=fact)
    return render_template('index.html')

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            name = 'Guest'
        feedback = request.form.get('feedback')
        date = datetime.datetime.now().strftime("%m-%d-%Y@%I:%M:%S")
        feedback_dict[date] = {'name': name,
                               'feedback': feedback}
        return redirect(url_for('show_feedback'))
    return render_template('feedback.html')

@app.route("/feedback/show")
def show_feedback():
    return render_template('show_feedback.html', feedback_dict=feedback_dict)

if __name__ == "__main__":
    app.run(debug=True)
