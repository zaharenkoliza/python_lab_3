build:   ; docker-compose build
pilot:   ; uv run python scripts/run_experiment.py configs/pilot.yaml && uv run python analysis/analyze.py results/pilot
full:    ; uv run python scripts/run_experiment.py configs/full.yaml && uv run python analysis/analyze.py results/raw
analyze: ; uv run python analysis/analyze.py $(DIR)
down:    ; docker-compose down -v
