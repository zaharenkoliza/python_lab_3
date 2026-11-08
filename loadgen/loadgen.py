"""Замкнутый генератор нагрузки: N виртуальных пользователей, без think time.

Нагрузка делится между несколькими процессами (--procs), клиент - aiohttp, чтобы сам
генератор не был узким местом. Пишет сырые данные по каждому запросу
(t, latency_ms, status, is_warmup) и метаданные, включая CPU генератора.
"""
import argparse, asyncio, csv, json, multiprocessing as mp, random, time

import aiohttp

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://app:8000")
p.add_argument("--workload", choices=["rows", "slow"], required=True)
p.add_argument("--users", type=int, required=True)
p.add_argument("--warmup", type=float, required=True)
p.add_argument("--duration", type=float, required=True)
p.add_argument("--seed", type=int, required=True)
p.add_argument("--procs", type=int, default=3)
p.add_argument("--out", required=True)


async def user(a, uid, session, t0, rows, stop_at):
    rng = random.Random(a.seed * 100003 + uid)  # воспроизводимая последовательность параметров
    while time.perf_counter() < stop_at:
        path = f"/rows?start={rng.randint(1, 9900)}" if a.workload == "rows" else "/slow"
        s = time.perf_counter()
        try:
            async with session.get(a.url + path) as r:
                await r.read()
                code = r.status
        except Exception:
            code = 0
        rows.append((round(s - t0, 4), round((time.perf_counter() - s) * 1000, 3), code))


async def shard(a, uids, t0):
    rows = []
    conn = aiohttp.TCPConnector(limit=len(uids))
    async with aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=30)) as s:
        stop_at = t0 + a.warmup + a.duration
        await asyncio.gather(*(user(a, u, s, t0, rows, stop_at) for u in uids))
    return rows


def worker(args):
    a, uids, t0 = args
    c0 = time.process_time()
    rows = asyncio.run(shard(a, uids, t0))
    return rows, time.process_time() - c0


if __name__ == "__main__":
    a = p.parse_args()
    procs = max(1, min(a.procs, a.users))
    shards = [list(range(i, a.users, procs)) for i in range(procs)]
    t0 = time.perf_counter() + 1.0  # общий старт для всех процессов (fork сохраняет часы)
    wall0 = time.perf_counter()
    with mp.Pool(procs) as pool:
        res = pool.map(worker, [(a, s, t0) for s in shards])
    wall = time.perf_counter() - wall0
    rows = sorted(r for rs, _ in res for r in rs)
    cpu_per_proc = [c / wall for _, c in res]
    with open(a.out + ".csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "latency_ms", "status", "is_warmup"])
        for t, l, c in rows:
            w.writerow([t, l, c, int(t < a.warmup)])
    json.dump({"loadgen_cpu_util": max(cpu_per_proc), "loadgen_cpu_total": sum(cpu_per_proc),
               "wall_s": wall, "n_requests": len(rows), **vars(a)}, open(a.out + ".loadgen.json", "w"))
