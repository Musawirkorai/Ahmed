
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize
 
# ---------------------- 1. Generator data ----------------------
gens = pd.DataFrame({
    "Gen":   ["G1", "G2", "G3", "G4"],
    "a":     [10,   12,   8,    15],     # fixed cost ($/hr)
    "b":     [2.0,  1.8,  2.2,  1.6],    # linear cost coeff ($/MWh)
    "c":     [0.004, 0.003, 0.005, 0.002], # quadratic coeff ($/MW^2h)
    "P_min": [10, 20, 15, 10],           # MW
    "P_max": [100, 150, 120, 130],       # MW
})
 
P_demand = 300  # MW total load to be supplied
 
# ---------------------- 2. Objective function ----------------------
def total_cost(P):
    return np.sum(gens["a"] + gens["b"] * P + gens["c"] * P**2)
 
# ---------------------- 3. Constraints & bounds ----------------------
constraints = [{"type": "eq", "fun": lambda P: np.sum(P) - P_demand}]
bounds = list(zip(gens["P_min"], gens["P_max"]))
P0 = np.full(len(gens), P_demand / len(gens))  # equal-split initial guess
 
#  sequential least squares programming alg
# ---------------------- 4. Solve ----------------------
result = minimize(total_cost, P0, method="SLSQP",
                   bounds=bounds, constraints=constraints)

 
gens["P_optimal"] = result.x
gens["Cost"] = gens["a"] + gens["b"] * gens["P_optimal"] + gens["c"] * gens["P_optimal"]**2
 
print(f"Optimal total cost: ${result.fun:,.2f}/hr\n")
print(gens[["Gen", "P_optimal", "Cost"]].round(2).to_string(index=False))
 
# ---------------------- 5. Visualization ----------------------
fig, ax = plt.subplots(1, 2, figsize=(12, 5))
 
# (a) Optimal power allocation per generator
ax[0].bar(gens["Gen"], gens["P_optimal"], color="teal")
ax[0].axhline(P_demand / len(gens), color="gray", ls="--", label="Equal split")
ax[0].set_ylabel("Power (MW)")
ax[0].set_title("Optimal Power Dispatch per Generator")
ax[0].legend()
 
# (b) Cost curves with optimal operating point marked
P_range = np.linspace(0, 160, 200)
for _, g in gens.iterrows():
    cost = g["a"] + g["b"] * P_range + g["c"] * P_range**2
    ax[1].plot(P_range, cost, label=g["Gen"])
    ax[1].scatter(g["P_optimal"], g["Cost"], color="black", zorder=5)
 
ax[1].set_xlabel("Power Output (MW)")
ax[1].set_ylabel("Cost ($/hr)")
ax[1].set_title("Generator Cost Curves & Optimal Points")
ax[1].legend()
 
plt.tight_layout()
plt.savefig("dispatch_result.png", dpi=150)
plt.show()
 