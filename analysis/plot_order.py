"""График пропускной способности по порядку прогонов: выявляет дрейф среды."""
import sys, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
d = sys.argv[1]
r = pd.read_csv(f"{d}/runs.csv").sort_values("order")
r["name"] = r.driver + "/" + r.workload
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for k, (w, g) in enumerate(r.groupby("workload")):
    for n, gg in g.groupby("driver"):
        ax[k].plot(gg.order, gg.rps, "o", label=n)
    ax[k].set_title(f"workload={w}"); ax[k].set_xlabel("порядок прогона"); ax[k].set_ylabel("RPS"); ax[k].grid(alpha=.3)
ax[0].legend(fontsize=8)
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=130)
