"""Печатает параметры машины и Docker в виде таблицы Markdown для раздела 6.3 отчёта.

Запуск на той машине, где выполняется эксперимент: make env
"""
import json, os, platform, subprocess


def sh(*c):
    try:
        return subprocess.run(c, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "не определено"


def cpu_model():
    if platform.system() == "Darwin":
        return sh("sysctl", "-n", "machdep.cpu.brand_string")
    for line in open("/proc/cpuinfo"):
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or "не определено"


def host_mem_gib():
    if platform.system() == "Darwin":
        return round(int(sh("sysctl", "-n", "hw.memsize")) / 2**30, 1)
    for line in open("/proc/meminfo"):
        if line.startswith("MemTotal"):
            return round(int(line.split()[1]) / 2**20, 1)


def info():
    d = json.loads(sh("docker", "info", "--format", "{{json .}}") or "{}")
    return {
        "Процессор": cpu_model(),
        "Ядер на хосте": os.cpu_count(),
        "ОЗУ хоста, ГиБ": host_mem_gib(),
        "ОС хоста": platform.platform(),
        "Docker Engine": d.get("ServerVersion", "не определено"),
        "Ядер, доступных Docker": d.get("NCPU", "не определено"),
        "ОЗУ, доступная Docker, ГиБ": round(d.get("MemTotal", 0) / 2**30, 1),
        "ОС внутри Docker": d.get("OperatingSystem", "не определено"),
        "Docker Compose": sh("docker-compose", "version", "--short") or sh("docker", "compose", "version", "--short"),
        "Python": platform.python_version(),
    }


if __name__ == "__main__":
    print("| Параметр | Значение |\n|---|---|")
    for k, v in info().items():
        print(f"| {k} | {v} |")
