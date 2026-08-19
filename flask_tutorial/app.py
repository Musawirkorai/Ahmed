"""
A tiny Flask app built for teaching.

Run it with:
    python app.py
Then open http://127.0.0.1:5000 in a browser.

The big idea:
    Browser  --HTTP request-->  Flask (Python)  --HTTP response-->  Browser

There are two different kinds of responses in this file:
  1. render_template(...) -> sends back a whole HTML PAGE (the browser navigates to it)
  2. jsonify(...)         -> sends back JSON DATA (JavaScript fetches it, no page reload)
"""

from flask import Flask, render_template, request, jsonify

# `app` is the web application object. __name__ tells Flask where to look
# for the `templates/` and `static/` folders (right next to this file).
app = Flask(__name__)


# ---------------------------------------------------------------------------
# "Database"
# ---------------------------------------------------------------------------
# A real app would use SQLite/Postgres. To keep the lesson focused we just use
# a Python list in memory. NOTE: restarting the server resets this list.
tasks = [
    {"id": 1, "title": "Learn what a route is", "done": True},
    {"id": 2, "title": "Send data with fetch()", "done": False},
]
next_id = 3  # simple counter for new task ids


# ---------------------------------------------------------------------------
# 1. A page route  ->  returns HTML
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    """@app.route("/") means: when someone visits the site root, run this function.

    render_template looks inside templates/ for the file, fills in the
    {{ placeholders }} with the values we pass, and returns the finished HTML.
    """
    return render_template("index.html", page_title="Flask + JS Demo", task_count=len(tasks))


# ---------------------------------------------------------------------------
# 2. A form route  ->  reads data the browser POSTed, returns HTML
# ---------------------------------------------------------------------------
@app.route("/greet", methods=["POST"])
def greet():
    """The classic (pre-JavaScript) way: an HTML <form> submits and the page reloads.

    `request.form` holds the fields of the submitted form, keyed by the
    `name` attribute of each <input>.
    """
    name = request.form.get("name", "").strip() or "stranger"
    return render_template("greet.html", name=name)


# ---------------------------------------------------------------------------
# 3. API routes  ->  return JSON, called from JavaScript with fetch()
# ---------------------------------------------------------------------------
@app.get("/api/tasks")
def list_tasks():
    """GET /api/tasks -> the whole list as JSON."""
    return jsonify(tasks)


@app.post("/api/tasks")
def add_task():
    """POST /api/tasks with a JSON body {"title": "..."} -> creates a task.

    `request.get_json()` parses the JSON the browser sent.
    The second value in the return tuple is the HTTP status code
    (201 = "Created"). Returning 400 signals "you sent me bad input".
    """
    global next_id
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()

    if not title:
        return jsonify({"error": "title is required"}), 400

    task = {"id": next_id, "title": title, "done": False}
    next_id += 1
    tasks.append(task)
    return jsonify(task), 201


@app.patch("/api/tasks/<int:task_id>")
def toggle_task(task_id):
    """PATCH /api/tasks/5 -> flip that task between done / not done.

    `<int:task_id>` is a URL variable: Flask pulls the number out of the URL
    and passes it into the function as an argument.
    """
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = not task["done"]
            return jsonify(task)
    return jsonify({"error": "task not found"}), 404


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    """DELETE /api/tasks/5 -> remove that task."""
    global tasks
    if not any(t["id"] == task_id for t in tasks):
        return jsonify({"error": "task not found"}), 404
    tasks = [t for t in tasks if t["id"] != task_id]
    return jsonify({"deleted": task_id})


# ---------------------------------------------------------------------------
# 4. A route with a query string  ->  /api/square?n=7
# ---------------------------------------------------------------------------
@app.get("/api/square")
def square():
    """`request.args` holds the ?key=value part of the URL."""
    raw = request.args.get("n", "0")
    try:
        n = float(raw)
    except ValueError:
        return jsonify({"error": f"'{raw}' is not a number"}), 400
    return jsonify({"input": n, "result": n * n})


# ---------------------------------------------------------------------------
# Start the development server
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # debug=True gives you auto-reload on save and a helpful error page.
    # Never use debug=True on a real public server.
    app.run(debug=True)
