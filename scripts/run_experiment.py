"""Раннер: строит план из YAML, рандомизирует порядок прогонов (seed), запускает стенд.

Для каждого прогона: пересоздать контейнер SUT с нужным DRIVER -> дождаться /health ->
запустить генератор -> параллельно собирать CPU/RAM SUT (docker stats) -> записать манифест.
Использование: python scripts/run_experiment.py configs/pilot.yaml
"""
import hashlib, os, itertools, json, random, subprocess, sys, threading, time, datetime, pathlib, platform
import yaml

DC = os.environ.get("COMPOSE", "docker-compose").split()  # в CI: COMPOSE="docker compose"


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout.strip()


def git_sha():
    try:
        return sh("git", "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        return "no-commits-yet"


def build_plan(cfg):
    f = cfg["factors"]
    configs = [dict(zip(f, v), label="") for v in itertools.product(*f.values())]
    if "aa" in cfg:
        configs += [dict(cfg["aa"], label="AA1"), dict(cfg["aa"], label="AA2")]
    plan = [dict(c, rep=r) for c in configs for r in range(cfg["repetitions"])]
    random.Random(cfg["seed"]).shuffle(plan)  # рандомизация порядка против дрейфа
    return plan


def wait_health(timeout=60):
    t = time.time()
    while time.time() - t < timeout:
        try:
            sh("docker", "exec", "sut", "python", "-c",
               "import urllib.request as u;u.urlopen('http://localhost:8000/health')")
            return
        except subprocess.CalledProcessError:
            time.sleep(1)
    raise RuntimeError("SUT не поднялся")


def sample_stats(stop, path):
    with open(path, "w") as f:
        f.write("ts,cpu_pct,mem_mib\n")
        while not stop.is_set():
            try:
                o = sh("docker", "stats", "--no-stream", "--format", "{{.CPUPerc}},{{.MemUsage}}", "sut")
                cpu, mem = o.split(",")
                f.write(f"{time.time():.1f},{cpu.strip('%')},{mem.split('/')[0].strip().replace('MiB','')}\n")
                f.flush()
            except Exception:
                pass


def main(cfg_path):
    cfg = yaml.safe_load(open(cfg_path))
    out = pathlib.Path(cfg["out_dir"]); out.mkdir(parents=True, exist_ok=True)
    plan = build_plan(cfg)
    env0 = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]}
    subprocess.run(DC + ["up", "-d", "--wait", "db"], check=True, capture_output=True, env=env0)  # БД должна быть готова
    env_info = {
        "git_sha": git_sha(),
        "host": platform.platform(), "docker": sh("docker", "version", "--format", "{{.Server.Version}}"),
        "app_image": sh("docker", "image", "inspect", "asyncbench-app:1", "--format", "{{.Id}}"),
        "db_image": "postgres:16.4",
        "init_sql_sha256": hashlib.sha256(open("db/init.sql", "rb").read()).hexdigest(),
    }
    json.dump({"config": cfg, "env": env_info, "plan": plan}, open(out / "plan.json", "w"), indent=1)
    for i, run in enumerate(plan):
        run_id = f"{i:04d}_{run['label'] or 'main'}_{run['driver']}_{run['workload']}_u{run['users']}_r{run['rep']}"
        base = f"/results/{out.name}/{run_id}" if out.parts[0] == "results" else None
        if (out / f"{run_id}.manifest.json").exists():
            continue  # возобновление прерванного прогона
        env = {"DRIVER": run["driver"], "POOL_SIZE": str(cfg["pool_size"]), "PATH": subprocess.os.environ["PATH"],
               "HOME": subprocess.os.environ["HOME"]}
        subprocess.run(DC + ["up", "-d", "--force-recreate", "--no-deps", "app"], check=True,
                       capture_output=True, env=env)
        wait_health()
        stop = threading.Event()
        th = threading.Thread(target=sample_stats, args=(stop, str(out / f"{run_id}.sut_stats.csv")))
        th.start()
        started = datetime.datetime.now().isoformat()
        subprocess.run(DC + ["--profile", "tools", "run", "--rm", "loadgen",
                             "--workload", run["workload"], "--users", str(run["users"]),
                             "--warmup", str(cfg["warmup_s"]), "--duration", str(cfg["duration_s"]),
                             "--seed", str(cfg["seed"] + i), "--out", base],
                       check=True, capture_output=True, env=env)
        stop.set(); th.join()
        json.dump({"run_id": run_id, "order": i, "started": started, **run}, open(out / f"{run_id}.manifest.json", "w"))
        print(f"[{i+1}/{len(plan)}] {run_id}", flush=True)


main(sys.argv[1])
