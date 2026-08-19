# Flask + HTML/CSS/JS — a teaching project

A deliberately small web app that shows how a Python backend and a browser
frontend talk to each other. Every file is commented for learning.

## Run it

```bash
pip install flask
python app.py
```

Open <http://127.0.0.1:5000>. Keep DevTools open (F12) on the **Network** tab —
you can watch each request leave the browser and see what Flask sends back.

## The files

```
flask_tutorial/
├── app.py                 # the backend: Python decides what to send
├── templates/             # Flask looks HERE for render_template()
│   ├── index.html         # the main page
│   └── greet.html         # the page the form sends you to
└── static/                # Flask serves THESE files as-is
    ├── css/style.css      # how it looks
    └── js/main.js         # code that runs in the browser
```

`templates/` and `static/` are not names you picked — Flask looks for exactly
those folder names next to `app.py`.

## The one idea to hold onto

```
Browser  ──── HTTP request  ───▶  Flask (Python)
         ◀─── HTTP response ────
```

Nothing else happens. A "web app" is just that loop, over and over. The only
question each time is *what* the response contains:

| Response | Flask function | What the browser does |
|---|---|---|
| A whole HTML page | `render_template(...)` | Throws away the old page, draws the new one |
| Just data (JSON) | `jsonify(...)` | Hands it to your JavaScript; page stays put |

## Walkthrough of the four demos

**1. Server-rendered data.** `app.py` passes `task_count` into
`render_template`. Jinja replaces `{{ task_count }}` with the number *before*
the HTML leaves the server. View page source: the placeholder is gone. Python
never runs in the browser.

**2. A plain HTML form.** `<form action="/greet" method="POST">` — the browser
itself sends the data and navigates to a new page. Python reads the fields with
`request.form.get("name")`. The `name` attribute on the `<input>` is the key.
This is how the whole web worked before JavaScript, and it still works fine.

**3. `fetch()` with a query string.** Clicking the button runs JS, which calls
`GET /api/square?n=7`. Python reads `?n=7` from `request.args`. Only one line of
the page changes — no reload. That difference *is* what people mean by a
"modern" web app.

**4. A JSON API.** The task list uses all four verbs:

| Verb | URL | Meaning |
|---|---|---|
| `GET` | `/api/tasks` | give me the list |
| `POST` | `/api/tasks` | here is a new one (data in the request body) |
| `PATCH` | `/api/tasks/3` | change task 3 |
| `DELETE` | `/api/tasks/3` | remove task 3 |

`<int:task_id>` in the route is a **URL variable** — Flask pulls the number out
of the URL and passes it into your function as an argument.

Note the two-part return: `return jsonify(task), 201`. The number is the HTTP
status code — `200` fine, `201` created, `400` your input was bad, `404` not
found. JavaScript checks it with `response.ok`.

## Things worth noticing

- **The data lives in a Python list**, so it resets every time the server
  restarts. Swapping that list for SQLite is the natural next step.
- **`textContent`, not `innerHTML`**, in `main.js`. `textContent` treats input
  as plain text, so a task named `<script>alert(1)</script>` displays as text
  instead of running. That is the XSS defence in one line.
- **`debug=True`** auto-reloads on save and shows a full error page. Great while
  learning, never on a public server — that error page lets visitors run code.
- **`url_for('static', filename='css/style.css')`** instead of typing the path.
  Flask builds the URL, so nothing breaks if the app later moves to a subpath.

## Exercises

1. Add an `/about` route that renders a new template.
2. Make the "Square it" box also return the cube.
3. Add an *edit* button to each task (`PUT /api/tasks/<id>` with a new title).
4. Show a message in the UI when the task list is empty.
5. Replace the `tasks` list with a SQLite table so data survives a restart.
