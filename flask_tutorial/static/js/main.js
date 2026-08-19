/* JavaScript runs INSIDE THE BROWSER (Python runs on the server).
   Its job here is to talk to Flask with fetch() and update the page
   without ever reloading it. */

// ---------------------------------------------------------------------------
// Grab the elements we need. document.getElementById finds them by id="...".
// ---------------------------------------------------------------------------
const squareInput = document.getElementById("square-input");
const squareBtn = document.getElementById("square-btn");
const squareOutput = document.getElementById("square-output");

const taskInput = document.getElementById("task-input");
const taskAddBtn = document.getElementById("task-add-btn");
const taskList = document.getElementById("task-list");
const taskError = document.getElementById("task-error");

// ---------------------------------------------------------------------------
// Demo 3: GET with a query string
// ---------------------------------------------------------------------------
// `async` lets us use `await`, which means "pause here until the server answers".
async function squareNumber() {
  const n = squareInput.value;

  // Sends: GET /api/square?n=7
  const response = await fetch(`/api/square?n=${encodeURIComponent(n)}`);
  const data = await response.json(); // parse the JSON body Python sent

  // response.ok is true for status codes 200-299.
  squareOutput.textContent = response.ok
    ? `${data.input} squared is ${data.result}`
    : `Error: ${data.error}`;
}

// "When this button is clicked, run that function."
squareBtn.addEventListener("click", squareNumber);

// ---------------------------------------------------------------------------
// Demo 4: the task list (GET / POST / PATCH / DELETE)
// ---------------------------------------------------------------------------

// Turn one task object into an <li> and put it on the page.
function renderTask(task) {
  const li = document.createElement("li");
  if (task.done) li.classList.add("done"); // CSS handles the strike-through

  const span = document.createElement("span");
  span.className = "title";
  // textContent (not innerHTML) — it treats the text as text, so a task
  // called "<script>..." can never run as code. This is how you avoid XSS.
  span.textContent = task.title;
  span.title = "Click to toggle done";
  span.addEventListener("click", () => toggleTask(task.id));

  const del = document.createElement("button");
  del.className = "delete-btn";
  del.textContent = "×";
  del.setAttribute("aria-label", `Delete ${task.title}`);
  del.addEventListener("click", () => deleteTask(task.id));

  li.append(span, del);
  taskList.append(li);
}

// Ask the server for the current list and redraw it from scratch.
async function loadTasks() {
  const response = await fetch("/api/tasks");
  const tasks = await response.json();

  taskList.innerHTML = ""; // clear whatever is there
  tasks.forEach(renderTask);
}

async function addTask() {
  const title = taskInput.value.trim();
  taskError.textContent = "";

  // POST needs more than a URL: the method, a header saying "this body is
  // JSON", and the body itself as a JSON string.
  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title }),
  });

  if (!response.ok) {
    const err = await response.json();
    taskError.textContent = err.error; // e.g. "title is required"
    return;
  }

  taskInput.value = "";
  await loadTasks();
}

async function toggleTask(id) {
  await fetch(`/api/tasks/${id}`, { method: "PATCH" });
  await loadTasks();
}

async function deleteTask(id) {
  await fetch(`/api/tasks/${id}`, { method: "DELETE" });
  await loadTasks();
}

taskAddBtn.addEventListener("click", addTask);

// Small nicety: pressing Enter in the box adds the task.
taskInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") addTask();
});

// ---------------------------------------------------------------------------
// Run once as soon as the script loads, so the list isn't empty.
// ---------------------------------------------------------------------------
loadTasks();
