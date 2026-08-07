"""
owfcr.py
--------
OWFCR model ("Optimal Wind Farm Cable Routing", Fischetti & Pisinger,
Networks 2018), extended with an electrically realistic cable model and
real-world (lat/lon) geography.

Cable types are no longer described by an arbitrary "capacity in turbines".
Instead each cable type carries its real electrical rating:

    voltage_kv     -- line voltage (kV), e.g. 33 or 66 for inter-array cables
    current_a      -- maximum continuous conductor current (A), driven by
                       conductor cross-section, insulation and installation
                       (burial depth, thermal resistivity, grouping...)
    power_factor   -- typical pf for the wind-farm export (~0.95-0.99)
    cost_per_m     -- installed cost per metre (EUR/m)

From these, the three-phase apparent power capacity is:

    S_mw = sqrt(3) * V_kv * I_a * pf / 1000

Each turbine is assigned a rated power (MW) instead of a flat "1 unit", so
the MILP capacity constraint enforces real MW flow <= cable's MW rating.

Distances are computed with the haversine formula on (lat, lon) pairs,
matching the real-world map used by the frontend.
"""

import math
import random

import pulp


# ----------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(coords, i, j):
    """Great-circle distance in metres between two (lat, lon) nodes."""
    lat1, lon1 = coords[i]
    lat2, lon2 = coords[j]
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def euclidean(coords, i, j):
    """Planar distance (kept for xy-based test instances / legacy use)."""
    xi, yi = coords[i]
    xj, yj = coords[j]
    return math.hypot(xi - xj, yi - yj)


def distance(coords, i, j, mode="latlon"):
    return haversine_m(coords, i, j) if mode == "latlon" else euclidean(coords, i, j)


def offset_latlon(lat, lon, dx_m, dy_m):
    """Shift a (lat, lon) point by dx_m east / dy_m north (small-distance approx)."""
    dlat = dy_m / EARTH_RADIUS_M
    dlon = dx_m / (EARTH_RADIUS_M * math.cos(math.radians(lat)))
    return lat + math.degrees(dlat), lon + math.degrees(dlon)


def make_instance(n_turbines=12, seed=1, center=(55.60, 7.85), radius_m=4000.0):
    """Random offshore-style instance around a real-world centre point.

    Default centre is close to the Horns Rev 3 site off Denmark, used as a
    reference layout in the original Fischetti & Pisinger paper.
    """
    random.seed(seed)
    coords = {0: center}
    turbines = list(range(1, n_turbines + 1))
    for t in turbines:
        ang = random.uniform(0, 2 * math.pi)
        r = radius_m * math.sqrt(random.uniform(0.1, 1.0))
        dx, dy = r * math.cos(ang), r * math.sin(ang)
        coords[t] = offset_latlon(center[0], center[1], dx, dy)
    return coords, turbines, 0


# ----------------------------------------------------------------------
# Electrical cable model
# ----------------------------------------------------------------------

def cable_capacity_mw(cable):
    """Three-phase apparent power rating of a cable type, in MW."""
    v_kv = cable["voltage_kv"]
    i_a = cable["current_a"]
    pf = cable.get("power_factor", 0.95)
    return math.sqrt(3) * v_kv * i_a * pf / 1000.0


# Reference catalogue: typical 33 kV / 66 kV offshore inter-array cables.
# current_a figures are representative continuous ratings for XLPE 3-core
# submarine cables at the given cross-section, buried ~1 m.
CABLE_TYPES = {
    "33kV_120mm2": {"voltage_kv": 33, "current_a": 300, "power_factor": 0.95,
                     "cost_per_m": 220, "cross_section_mm2": 120},
    "33kV_400mm2": {"voltage_kv": 33, "current_a": 545, "power_factor": 0.95,
                     "cost_per_m": 340, "cross_section_mm2": 400},
    "66kV_500mm2": {"voltage_kv": 66, "current_a": 620, "power_factor": 0.95,
                     "cost_per_m": 480, "cross_section_mm2": 500},
}


# ----------------------------------------------------------------------
# MILP model (OWFCR)
# ----------------------------------------------------------------------

def solve_owfcr(coords, turbines, substation, cable_types=CABLE_TYPES,
                 max_cables_at_substation=4, time_limit=60,
                 turbine_power_mw=8.0, coord_mode="latlon"):
    """Solve the OWFCR model with electrically-rated cables.

    turbine_power_mw: either a single float applied to every turbine, or a
    dict {turbine_id: mw} for a mixed-capacity farm.
    """

    V = [substation] + turbines
    A = [(i, j) for i in V for j in V if i != j]
    T = list(cable_types.keys())

    if isinstance(turbine_power_mw, dict):
        P = {h: float(turbine_power_mw.get(h, 8.0)) for h in turbines}
    else:
        P = {h: float(turbine_power_mw) for h in turbines}

    dist_m = {(i, j): distance(coords, i, j, coord_mode) for (i, j) in A}
    cost = {(i, j, t): cable_types[t]["cost_per_m"] * dist_m[(i, j)]
            for (i, j) in A for t in T}
    capacity_mw = {t: cable_capacity_mw(cable_types[t]) for t in T}

    prob = pulp.LpProblem("OWFCR", pulp.LpMinimize)

    x = pulp.LpVariable.dicts("x", (A, T), cat="Binary")
    y = pulp.LpVariable.dicts("y", A, cat="Binary")
    f = pulp.LpVariable.dicts("f", A, lowBound=0)  # flow in MW

    # objective (1): minimize total cable cost
    prob += pulp.lpSum(cost[(i, j, t)] * x[(i, j)][t] for (i, j) in A for t in T)

    # (2) one cable type per built arc, defines y
    for (i, j) in A:
        prob += pulp.lpSum(x[(i, j)][t] for t in T) == y[(i, j)]

    # (3) flow conservation for turbines (MW produced -> exported)
    for h in turbines:
        out_flow = pulp.lpSum(f[(h, j)] for j in V if j != h)
        in_flow = pulp.lpSum(f[(i, h)] for i in V if i != h)
        prob += out_flow - in_flow == P[h]

    # (4) capacity: MW flow on an arc cannot exceed the installed cable rating
    for (i, j) in A:
        prob += pulp.lpSum(capacity_mw[t] * x[(i, j)][t] for t in T) >= f[(i, j)]

    # (5) exactly one cable leaves every turbine
    for h in turbines:
        prob += pulp.lpSum(y[(h, j)] for j in V if j != h) == 1

    # (6) no cable leaves the substation
    prob += pulp.lpSum(y[(substation, j)] for j in V if j != substation) == 0

    # (9) at most C cables enter the substation
    prob += pulp.lpSum(y[(i, substation)] for i in V if i != substation) \
            <= max_cables_at_substation

    # EXTEND HERE: no-crossing constraints, string-structure, branching
    # penalties, closed-loop or OTM variants from the paper.

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit)
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    total_cost = pulp.value(prob.objective)

    chosen_arcs = []
    for (i, j) in A:
        for t in T:
            v = pulp.value(x[(i, j)][t])
            if v and v > 0.5:
                power_mw = pulp.value(f[(i, j)]) or 0.0
                cap = capacity_mw[t]
                chosen_arcs.append({
                    "i": i, "j": j, "cable_type": t,
                    "distance_m": dist_m[(i, j)],
                    "power_mw": power_mw,
                    "capacity_mw": cap,
                    "utilization": (power_mw / cap) if cap > 0 else 0.0,
                })

    return {
        "status": status,
        "total_cost": total_cost,
        "arcs": chosen_arcs,
        "capacity_mw": capacity_mw,
    }


# ----------------------------------------------------------------------
# CLI demo
# ----------------------------------------------------------------------

if __name__ == "__main__":
    coords, turbines, substation = make_instance(n_turbines=12, seed=7)

    result = solve_owfcr(
        coords, turbines, substation,
        cable_types=CABLE_TYPES,
        max_cables_at_substation=4,
        time_limit=60,
        turbine_power_mw=8.0,
    )

    print(f"Solver status : {result['status']}")
    print(f"Total cost    : {result['total_cost']:,.0f} EUR\n")
    print(f"{'from':>5} {'to':>5} {'cable':>14} {'length (m)':>12} {'MW':>8} {'util%':>7}")
    for a in sorted(result["arcs"], key=lambda a: (a["i"], a["j"])):
        print(f"{a['i']:>5} {a['j']:>5} {a['cable_type']:>14} "
              f"{a['distance_m']:>12.1f} {a['power_mw']:>8.2f} "
              f"{a['utilization'] * 100:>6.1f}%")