"""Анализ: сырые CSV -> метрики на прогон -> статистика по конфигурациям.

Единица анализа - прогон (p95 за прогон), а не отдельный запрос.
Usage: python analysis/analyze.py results/pilot
"""
import glob, json, sys, pathlib
import numpy as np, pandas as pd
from scipy import stats

d = pathlib.Path(sys.argv[1])
rows = []
for m in sorted(glob.glob(str(d / "*.manifest.json"))):
    man = json.load(open(m)); rid = man["run_id"]
    df = pd.read_csv(d / f"{rid}.csv"); lg = json.load(open(d / f"{rid}.loadgen.json"))
    df = df[df.is_warmup == 0]
    ok = df[df.status == 200]
    dur = lg["duration"]
    st = pd.read_csv(d / f"{rid}.sut_stats.csv")
    rows.append(dict(man, rps=len(ok) / dur, p50=ok.latency_ms.quantile(.5), p95=ok.latency_ms.quantile(.95),
                     p99=ok.latency_ms.quantile(.99), err_pct=100 * (len(df) - len(ok)) / max(len(df), 1),
                     sut_cpu=st.cpu_pct.median(), sut_mem=st.mem_mib.median(), gen_cpu=100 * lg["loadgen_cpu_util"]))
runs = pd.DataFrame(rows); runs.to_csv(d / "runs.csv", index=False)
runs["cfg"] = runs.label.where(runs.label != "", "") + runs.driver + "|" + runs.workload + "|u" + runs.users.astype(str)


def boot_ci(x, f=np.median, n=5000, seed=1):
    rng = np.random.default_rng(seed); x = np.asarray(x)
    b = [f(rng.choice(x, len(x))) for _ in range(n)]
    return np.percentile(b, [2.5, 97.5])


out = []
for cfg, g in runs.groupby("cfg"):
    lo, hi = boot_ci(g.p95)
    out.append(dict(cfg=cfg, n=len(g), rps_med=g.rps.median(), p95_med=g.p95.median(), p95_lo=lo, p95_hi=hi,
                    p95_cv_pct=100 * g.p95.std() / g.p95.mean(), sut_cpu=g.sut_cpu.median(),
                    gen_cpu_max=g.gen_cpu.max(), err_max=g.err_pct.max()))
summ = pd.DataFrame(out); summ.to_csv(d / "summary.csv", index=False)
print(summ.round(2).to_string(index=False))


def cmp(a, b, metric):
    x, y = runs[runs.cfg == a][metric], runs[runs.cfg == b][metric]
    u = stats.mannwhitneyu(x, y, alternative="two-sided")
    delta = (np.sum(x.values[:, None] > y.values[None, :]) - np.sum(x.values[:, None] < y.values[None, :])) / (len(x) * len(y))
    return u.pvalue, delta, x.median() / y.median()


print("\n== A/A-тест (p95 и RPS) ==")
for met in ("p95", "rps"):
    a1 = [c for c in runs.cfg.unique() if c.startswith("AA1")]; a2 = [c for c in runs.cfg.unique() if c.startswith("AA2")]
    if a1 and a2:
        p, dl, r = cmp(a1[0], a2[0], met)
        print(f"{met}: p={p:.3f}, Cliff's delta={dl:.2f}, ratio medians={r:.3f}")

print("\n== Драйвер vs базовый sync_psycopg2 (RPS, p95): Mann-Whitney, Cliff's delta, отношение медиан ==")
main = runs[runs.label == ""]
res = []
for (w, u), _ in main.groupby(["workload", "users"]):
    base = f"sync_psycopg2|{w}|u{u}"
    for drv in ("async_asyncpg", "async_psycopg3"):
        c = f"{drv}|{w}|u{u}"
        if (runs.cfg == base).any() and (runs.cfg == c).any():
            for met in ("rps", "p95"):
                p, dl, r = cmp(c, base, met)
                res.append((w, u, drv, met, r, dl, p))
# поправка Holm на множественные сравнения
order = np.argsort([x[-1] for x in res]); m = len(res); adj = [0] * m; run_max = 0
for rank, i in enumerate(order):
    run_max = max(run_max, min(1, (m - rank) * res[i][-1])); adj[i] = run_max
for x, pa in zip(res, adj):
    print(f"{x[0]:5s} u={x[1]:<3d} {x[2]:15s} {x[3]:3s}: ratio={x[4]:.2f} delta={x[5]:+.2f} p={x[6]:.4f} p_holm={pa:.4f}")
