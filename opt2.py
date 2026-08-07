
# Economic Cable Size Selection (Kelvin's Law) - a simple optimization example
# Problem: A cable carries current I over a distance L. A THICKER cable costs
# more to buy, but a THINNER cable wastes more energy as heat (I^2 * R losses).

# We want the cable cross-sectional area (mm^2) that gives the LOWEST total
# annual cost = (cost of buying the cable) + (cost of the energy it wastes).

# Method: try many possible areas and simply pick the one with lowest total
# cost (a "brute-force" search) -- no fancy solver needed, easy to follow.


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------- 1. Given data ----------------------
I = 100          # current carried by the cable, Amps
L = 500           # cable length, meters
rho = 1.68e-8     # copper resistivity, ohm*m
hours_per_year = 4000     # hours the cable operates per year
price_per_kWh = 0.15      # $/kWh
cable_cost_per_mm2_per_m = 0.08   # $ to buy 1 mm^2 of cable, per meter
years = 15                 # how many years we spread the cable cost over

# ---------------------- 2. Try a range of possible cable sizes ----------------------
area = np.linspace(10, 150, 300)   # candidate cross-sections, mm^2 (10 to 150)

# Cost of buying the cable, spread evenly over its lifetime ($/year)
investment_cost = (cable_cost_per_mm2_per_m * area * L) / years

# Resistance drops as area increases -> so does the energy wasted as heat
R = rho * L / (area * 1e-6)             # ohms  (area converted mm^2 -> m^2)
power_loss_kW = (I**2 * R) / 1000       # kW wasted as heat
loss_cost = power_loss_kW * hours_per_year * price_per_kWh   # $/year

total_cost = investment_cost + loss_cost

# ---------------------- 3. Find the cheapest option ----------------------
best_i = np.argmin(total_cost)
best_area = area[best_i]
best_cost = total_cost[best_i]

print(f"Optimal cable size:  {best_area:.1f} mm^2")
print(f"  Investment cost:   ${investment_cost[best_i]:.2f}/year")
print(f"  Energy loss cost:  ${loss_cost[best_i]:.2f}/year")
print(f"  TOTAL cost:        ${best_cost:.2f}/year")

df = pd.DataFrame({"Area_mm2": area, "Investment": investment_cost,
                    "Loss": loss_cost, "Total": total_cost})
print("\nSample of results:")
print(df.iloc[::50].round(2).to_string(index=False))

# ---------------------- 4. Visualization ----------------------
plt.figure(figsize=(8, 5))
plt.plot(area, investment_cost, label="Investment Cost", color="steelblue")
plt.plot(area, loss_cost, label="Energy Loss Cost", color="orangered")
plt.plot(area, total_cost, label="Total Cost", color="black", linewidth=2)
plt.scatter(best_area, best_cost, color="green", zorder=5,
            label=f"Optimal: {best_area:.0f} mm²")

plt.xlabel("Cable Cross-Sectional Area (mm²)")
plt.ylabel("Annual Cost ($/year)")
plt.title("Economic Cable Size Selection")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("cable_size_optimization.png", dpi=150)
plt.show()