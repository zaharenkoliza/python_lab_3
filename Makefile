build:   ; docker-compose build
pilot:   ; uv run python scripts/run_experiment.py configs/pilot.yaml && uv run python analysis/analyze.py results/pilot && uv run python analysis/plot_order.py results/pilot docs/pilot_order.png
full:    ; uv run python scripts/run_experiment.py configs/full.yaml && uv run python analysis/analyze.py results/raw
analyze: ; uv run python analysis/analyze.py $(DIR)
down:    ; docker-compose down -v
env:     ; uv run python scripts/collect_env.py
