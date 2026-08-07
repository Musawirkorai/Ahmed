/* OWFCR frontend logic (Leaflet edition)
 * ---------------------------------------
 * State: a substation + turbines, each with real {lat, lon}. Markers live
 * on a Leaflet/OSM map. Cables are rated by voltage (kV) + current (A),
 * matching real submarine inter-array cable datasheets.
 */

const SQRT3 = Math.sqrt(3);
function capacityMw(v_kv, i_a, pf) { return (SQRT3 * v_kv * i_a * pf) / 1000; }

let substation = { id: 0, lat: window.DEFAULT_CENTER.lat, lon: window.DEFAULT_CENTER.lon };
let turbines = [];          // {id, lat, lon}
let nextId = 1;
let selectedId = null;      // node id or null (0 = substation)
let lastSolution = null;    // arcs from the last solve (cleared on edit)

let markers = new Map();    // id -> Leaflet marker
let cableLines = [];        // Leaflet polylines from the last solve

/* ---------- map setup ---------- */
const map = L.map("farm", { zoomControl: true }).setView(
  [window.DEFAULT_CENTER.lat, window.DEFAULT_CENTER.lon], 13
);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

function turbineIcon(sel) {
  return L.divIcon({
    className: "",
    html: `<div class="marker-turbine${sel ? " selected" : ""}"></div>`,
    iconSize: [18, 18], iconAnchor: [9, 9],
  });
}
function subIcon(sel) {
  return L.divIcon({
    className: "",
    html: `<div class="marker-sub${sel ? " selected" : ""}">SUB</div>`,
    iconSize: [40, 22], iconAnchor: [20, 11],
  });
}

function nodeById(id) { return id === 0 ? substation : turbines.find(t => t.id === id); }

/* ---------- rendering ---------- */
function render() {
  // clear old markers
  for (const m of markers.values()) map.removeLayer(m);
  markers.clear();

  // substation
  const subM = L.marker([substation.lat, substation.lon], {
    icon: subIcon(selectedId === 0), draggable: true,
  }).addTo(map);
  subM.on("dragend", () => {
    const p = subM.getLatLng();
    substation.lat = p.lat; substation.lon = p.lng;
    invalidateSolution();
  });
  subM.on("click", (e) => { L.DomEvent.stopPropagation(e); selectedId = 0; render(); });
  markers.set(0, subM);

  // turbines
  for (const t of turbines) {
    const tm = L.marker([t.lat, t.lon], {
      icon: turbineIcon(selectedId === t.id), draggable: true,
    }).addTo(map);
    tm.bindTooltip(String(t.id), { permanent: false, direction: "top" });
    tm.on("dragend", () => {
      const p = tm.getLatLng();
      t.lat = p.lat; t.lon = p.lng;
      invalidateSolution();
    });
    tm.on("click", (e) => { L.DomEvent.stopPropagation(e); selectedId = t.id; render(); });
    markers.set(t.id, tm);
  }

  document.getElementById("turbCount").textContent = turbines.length;
  document.getElementById("btnDelete").disabled = !(selectedId !== null && selectedId !== 0);
  updateFarmMwHint();
}

function drawCables(arcs) {
  for (const l of cableLines) map.removeLayer(l);
  cableLines = [];
  for (const a of arcs) {
    const from = nodeById(a.i), to = nodeById(a.j);
    if (!from || !to) continue;
    const weight = 2 + Math.min(4, (a.utilization || 0) / 25);
    const line = L.polyline(
      [[from.lat, from.lon], [to.lat, to.lon]],
      { color: a.color, weight, opacity: 0.9 }
    ).addTo(map);
    line.bindTooltip(`${a.type} &middot; ${a.power_mw} MW (${a.utilization}%)`);
    cableLines.push(line);
  }
}

/* ---------- interaction: click empty map to add a turbine ---------- */
map.on("click", (e) => {
  turbines.push({ id: nextId++, lat: e.latlng.lat, lon: e.latlng.lng });
  selectedId = null;
  invalidateSolution();
  render();
});

document.getElementById("btnClear").addEventListener("click", () => {
  turbines = []; nextId = 1; selectedId = null; invalidateSolution(); render();
});
document.getElementById("btnDelete").addEventListener("click", deleteSelected);
document.addEventListener("keydown", (e) => {
  if ((e.key === "Delete" || e.key === "Backspace") && selectedId !== null && selectedId !== 0) {
    e.preventDefault(); deleteSelected();
  }
});
function deleteSelected() {
  if (selectedId === null || selectedId === 0) return;
  turbines = turbines.filter(t => t.id !== selectedId);
  selectedId = null; invalidateSolution(); render();
}

document.getElementById("btnRandom").addEventListener("click", async () => {
  const n = parseInt(document.getElementById("randCount").value, 10) || 12;
  const radius = parseInt(document.getElementById("randRadius").value, 10) || 4000;
  const c = map.getCenter();
  const res = await fetch(`/api/example?n=${n}&radius_m=${radius}&lat=${c.lat}&lon=${c.lng}`);
  const data = await res.json();
  substation = data.substation;
  turbines = data.turbines;
  nextId = Math.max(0, ...turbines.map(t => t.id)) + 1;
  selectedId = null; invalidateSolution(); render();
});

/* ---------- cable catalogue table ---------- */
const cableBody = document.getElementById("cableBody");
const PALETTE = ["#e74c3c", "#2ecc71", "#3498db", "#f1c40f", "#9b59b6", "#e67e22"];

function addCableRow(name, v_kv, i_a, pf, cost, color) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input type="color" value="${color}"></td>
    <td><input type="text" value="${name}" class="name-in"></td>
    <td><input type="number" min="1" step="1" value="${v_kv}" class="kv-in mini"></td>
    <td><input type="number" min="1" step="10" value="${i_a}" class="a-in mini"></td>
    <td><input type="number" min="0.1" max="1" step="0.01" value="${pf}" class="pf-in mini"></td>
    <td><input type="number" min="0" step="1" value="${cost}" class="cost-in"></td>
    <td class="cap-out">–</td>
    <td><button class="row-del" title="Remove">&times;</button></td>`;
  tr.querySelector(".row-del").addEventListener("click", () => {
    tr.remove(); invalidateSolution(); updateFarmMwHint();
  });
  tr.querySelectorAll("input").forEach(i => i.addEventListener("input", () => {
    invalidateSolution(); updateCapOut(tr);
  }));
  cableBody.appendChild(tr);
  updateCapOut(tr);
}

function updateCapOut(tr) {
  const v = parseFloat(tr.querySelector(".kv-in").value) || 0;
  const a = parseFloat(tr.querySelector(".a-in").value) || 0;
  const pf = parseFloat(tr.querySelector(".pf-in").value) || 0;
  tr.querySelector(".cap-out").textContent = capacityMw(v, a, pf).toFixed(1) + " MW";
}

document.getElementById("btnAddCable").addEventListener("click", () => {
  const i = cableBody.children.length;
  addCableRow("cable" + (i + 1), 33, 400, 0.95, 300, PALETTE[i % PALETTE.length]);
});

function readCables() {
  const rows = [...cableBody.children];
  return rows.map(tr => ({
    color: tr.querySelector('input[type=color]').value,
    name: tr.querySelector('.name-in').value,
    voltage_kv: parseFloat(tr.querySelector('.kv-in').value),
    current_a: parseFloat(tr.querySelector('.a-in').value),
    power_factor: parseFloat(tr.querySelector('.pf-in').value),
    cost_per_m: parseFloat(tr.querySelector('.cost-in').value),
  })).filter(c => c.name.trim());
}

/* ---------- farm MW hint ---------- */
function updateFarmMwHint() {
  const mw = parseFloat(document.getElementById("turbineMw").value) || 0;
  const total = mw * turbines.length;
  document.getElementById("farmMwHint").textContent =
    `= ${total.toFixed(1)} MW total farm output`;
}
document.getElementById("turbineMw").addEventListener("input", () => {
  updateFarmMwHint(); invalidateSolution();
});

/* ---------- solving ---------- */
const statusPill = document.getElementById("statusPill");
const errBox = document.getElementById("errBox");
const results = document.getElementById("results");
const btnSolve = document.getElementById("btnSolve");

function setStatus(text, cls) { statusPill.textContent = text; statusPill.className = "status-pill " + (cls || ""); }
function invalidateSolution() {
  if (lastSolution) {
    lastSolution = null; results.classList.add("hidden"); setStatus("Ready");
    for (const l of cableLines) map.removeLayer(l);
    cableLines = [];
  }
}

btnSolve.addEventListener("click", async () => {
  errBox.textContent = "";
  if (turbines.length === 0) { errBox.textContent = "Add at least one turbine first."; return; }
  const cables = readCables();
  if (cables.length === 0) { errBox.textContent = "Define at least one cable type."; return; }

  const payload = {
    turbines, substation, cable_types: cables,
    max_cables: parseInt(document.getElementById("maxCables").value, 10) || 4,
    time_limit: parseInt(document.getElementById("timeLimit").value, 10) || 30,
    turbine_power_mw: parseFloat(document.getElementById("turbineMw").value) || 8,
  };

  btnSolve.disabled = true;
  setStatus("Optimizing…", "busy");
  try {
    const res = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      errBox.textContent = data.error || "Solver error.";
      setStatus("Error", "err");
      return;
    }
    lastSolution = data.arcs;
    drawCables(data.arcs);
    showResults(data);
    setStatus(`${data.status} · €${fmt(data.total_cost)}`, "ok");
  } catch (err) {
    errBox.textContent = "Request failed: " + err.message;
    setStatus("Error", "err");
  } finally {
    btnSolve.disabled = false;
  }
});

function showResults(data) {
  results.classList.remove("hidden");
  document.getElementById("kpiCost").textContent = "€" + fmt(data.total_cost);
  document.getElementById("kpiCables").textContent = data.n_cables;
  document.getElementById("kpiTime").textContent = data.solve_time + "s";

  const cableMeta = {};
  readCables().forEach(c => cableMeta[c.name] = c.color);

  const sBody = document.getElementById("summaryBody");
  sBody.innerHTML = "";
  for (const [name, s] of Object.entries(data.summary)) {
    if (s.count === 0) continue;
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><span class="swatch" style="background:${cableMeta[name] || '#888'}"></span>${name}</td>
      <td>${s.count}</td><td>${fmt(s.length)} m</td><td>${s.power_mw} MW</td><td>€${fmt(s.cost)}</td>`;
    sBody.appendChild(tr);
  }

  const aBody = document.getElementById("arcBody");
  aBody.innerHTML = "";
  for (const a of data.arcs) {
    const from = a.i === 0 ? "SUB" : a.i;
    const to = a.j === 0 ? "SUB" : a.j;
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${from}</td><td>${to}</td>
      <td><span class="swatch" style="background:${a.color}"></span>${a.type}</td>
      <td>${fmt(a.length)}</td><td>${a.power_mw}</td><td>${a.utilization}%</td><td>€${fmt(a.cost)}</td>`;
    aBody.appendChild(tr);
  }
}

function fmt(n) { return Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 }); }

/* ---------- init ---------- */
(function init() {
  const def = window.DEFAULT_CABLES || {};
  const colors = { "33kV_120mm2": "#333333", "33kV_400mm2": "#2e8b57", "66kV_500mm2": "#3498db" };
  let i = 0;
  for (const [name, c] of Object.entries(def)) {
    addCableRow(name, c.voltage_kv, c.current_a, c.power_factor, c.cost_per_m,
                colors[name] || PALETTE[i % PALETTE.length]);
    i++;
  }
  if (i === 0) { addCableRow("33kV_120mm2", 33, 300, 0.95, 220, PALETTE[0]); }

  // seed with a random layout so the page isn't empty
  fetch(`/api/example?n=10&radius_m=4000&lat=${window.DEFAULT_CENTER.lat}&lon=${window.DEFAULT_CENTER.lon}`)
    .then(r => r.json())
    .then(d => {
      substation = d.substation; turbines = d.turbines;
      nextId = Math.max(0, ...turbines.map(t => t.id)) + 1;
      render();
    })
    .catch(() => render());
})();