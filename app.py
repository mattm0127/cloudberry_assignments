from flask import Flask, render_template, redirect, url_for, request

app = Flask(__name__)


# Can also be done with one function and a return render_template('about.html', kwargs)
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get('name')
        fact = request.form.get('fact')
        return redirect(url_for('about', name=name, fact=fact))
    return render_template('index.html')

@app.route("/about")
def about():
    name = request.args.get('name', 'Guest')
    fact = request.args.get('fact')
    return render_template('about.html', name=name, fact=fact)


if __name__ == "__main__":
    app.run(debug=True)
