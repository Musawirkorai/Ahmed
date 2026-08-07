"""
app.py -- Web frontend for the OWFCR cable optimizer.
-----------------------------------------------------
A small Flask server that wraps the MILP solver in ``owfcr.py`` and exposes
it to an interactive browser UI. The user places wind turbines / the
substation on a real map, edits the cable catalogue (voltage/current
rated), and the server solves the Optimal Wind Farm Cable Routing problem
and returns the chosen cables so the page can draw them.

Run:
    python app.py
Then open http://127.0.0.1:5000 in a browser.
"""

import time

from flask import Flask, jsonify, render_template, request

from owfcr import cable_capacity_mw, make_instance, solve_owfcr, CABLE_TYPES

app = Flask(__name__)

# Default map centre: offshore Horns Rev 3, Denmark -- matches the paper's
# reference case and gives a sensible open-water starting view.
DEFAULT_CENTER = {"lat": 55.60, "lon": 7.85}


# ----------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------

@app.route("/")
def index():
    default_cables = {
        name: {**c, "capacity_mw": round(cable_capacity_mw(c), 2)}
        for name, c in CABLE_TYPES.items()
    }
    return render_template(
        "index.html",
        default_cables=default_cables,
        default_center=DEFAULT_CENTER,
    )


# ----------------------------------------------------------------------
# API: generate a random offshore wind-farm layout around a map point
# ----------------------------------------------------------------------

@app.route("/api/example")
def api_example():
    n = int(request.args.get("n", 12))
    n = max(2, min(n, 40))
    seed = int(request.args.get("seed", 0)) or None
    lat = float(request.args.get("lat", DEFAULT_CENTER["lat"]))
    lon = float(request.args.get("lon", DEFAULT_CENTER["lon"]))
    radius_m = float(request.args.get("radius_m", 4000))

    import random
    if seed is None:
        seed = random.randint(0, 9999)

    coords, turbine_ids, sub_id = make_instance(
        n_turbines=n, seed=seed, center=(lat, lon), radius_m=radius_m,
    )

    turbines = [{"id": t, "lat": coords[t][0], "lon": coords[t][1]} for t in turbine_ids]
    return jsonify({
        "seed": seed,
        "substation": {"id": sub_id, "lat": lat, "lon": lon},
        "turbines": turbines,
    })


# ----------------------------------------------------------------------
# API: solve the OWFCR model for the submitted layout
# ----------------------------------------------------------------------

@app.route("/api/solve", methods=["POST"])
def api_solve():
    data = request.get_json(force=True)

    try:
        raw_turbines = data["turbines"]
        raw_sub = data["substation"]
        raw_cables = data["cable_types"]
        max_cables = int(data.get("max_cables", 4))
        time_limit = max(1, min(int(data.get("time_limit", 30)), 300))
        turbine_mw = float(data.get("turbine_power_mw", 8.0))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": f"Bad request: {exc}"}), 400

    if len(raw_turbines) < 1:
        return jsonify({"error": "Add at least one turbine."}), 400
    if not raw_cables:
        return jsonify({"error": "Define at least one cable type."}), 400
    if turbine_mw <= 0:
        return jsonify({"error": "Turbine rated power must be > 0 MW."}), 400

    # Build the coordinate dictionary the solver expects (lat/lon nodes).
    substation = int(raw_sub["id"])
    coords = {substation: (float(raw_sub["lat"]), float(raw_sub["lon"]))}
    turbines = []
    for t in raw_turbines:
        tid = int(t["id"])
        coords[tid] = (float(t["lat"]), float(t["lon"]))
        turbines.append(tid)

    # Cable catalogue: voltage (kV) + current rating (A) drive capacity.
    cable_types = {}
    for c in raw_cables:
        name = str(c["name"]).strip()
        if not name:
            continue
        try:
            v_kv = float(c["voltage_kv"])
            i_a = float(c["current_a"])
            pf = float(c.get("power_factor", 0.95))
            cost_per_m = float(c["cost_per_m"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": f"Cable '{name}' has invalid electrical fields."}), 400

        if v_kv <= 0 or i_a <= 0:
            return jsonify({"error": f"Cable '{name}' needs voltage_kv and current_a > 0."}), 400
        if not (0 < pf <= 1):
            return jsonify({"error": f"Cable '{name}' power_factor must be in (0, 1]."}), 400

        cable_types[name] = {
            "voltage_kv": v_kv,
            "current_a": i_a,
            "power_factor": pf,
            "cost_per_m": cost_per_m,
            "color": c.get("color", "#666666"),
        }

    # Feasibility pre-check: the substation must be able to absorb total farm
    # output through the allowed number of cables (using the best cable's MW
    # rating as an upper bound -- a necessary, not sufficient, check).
    best_cap_mw = max(cable_capacity_mw(v) for v in cable_types.values())
    total_farm_mw = turbine_mw * len(turbines)
    if max_cables * best_cap_mw < total_farm_mw:
        return jsonify({
            "error": (
                f"Infeasible: {len(turbines)} turbines x {turbine_mw:.1f} MW = "
                f"{total_farm_mw:.1f} MW cannot be exported through "
                f"{max_cables} cables of max rating {best_cap_mw:.1f} MW "
                f"({max_cables * best_cap_mw:.1f} MW total). Raise 'max cables', "
                f"turbine power, or cable rating."
            )
        }), 400

    t0 = time.time()
    result = solve_owfcr(
        coords, turbines, substation,
        cable_types=cable_types,
        max_cables_at_substation=max_cables,
        time_limit=time_limit,
        turbine_power_mw=turbine_mw,
        coord_mode="latlon",
    )
    elapsed = time.time() - t0

    if result["status"] not in ("Optimal", "Not Solved") or result["total_cost"] is None:
        return jsonify({
            "status": result["status"],
            "error": f"No solution found (solver status: {result['status']}).",
        }), 200

    # Per-cable-type summary for the results panel.
    summary = {name: {"count": 0, "length": 0.0, "cost": 0.0, "power_mw": 0.0}
               for name in cable_types}
    arcs = []
    for a in result["arcs"]:
        ctype = a["cable_type"]
        length = a["distance_m"]
        cost = cable_types[ctype]["cost_per_m"] * length
        arcs.append({
            "i": a["i"], "j": a["j"], "type": ctype,
            "length": round(length, 1),
            "cost": round(cost, 2),
            "power_mw": round(a["power_mw"], 2),
            "capacity_mw": round(a["capacity_mw"], 2),
            "utilization": round(a["utilization"] * 100, 1),
            "color": cable_types[ctype]["color"],
        })
        summary[ctype]["count"] += 1
        summary[ctype]["length"] += length
        summary[ctype]["cost"] += cost
        summary[ctype]["power_mw"] += a["power_mw"]

    for s in summary.values():
        s["length"] = round(s["length"], 1)
        s["cost"] = round(s["cost"], 2)
        s["power_mw"] = round(s["power_mw"], 2)

    return jsonify({
        "status": result["status"],
        "total_cost": round(result["total_cost"], 2),
        "arcs": arcs,
        "summary": summary,
        "solve_time": round(elapsed, 2),
        "n_cables": len(arcs),
        "total_farm_mw": round(total_farm_mw, 2),
        "cable_capacity_mw": {k: round(v, 2) for k, v in result["capacity_mw"].items()},
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)