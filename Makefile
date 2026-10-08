.PHONY: start stop test lint format

start:
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 || ./run.sh

stop:
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 -Down || docker compose down

test:
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 -TestOnly

lint:
	.\.venv\Scripts\ruff.exe check backend/
	.\.venv\Scripts\bandit.exe -c pyproject.toml -r backend/

format:
	.\.venv\Scripts\black.exe backend/
	.\.venv\Scripts\ruff.exe check --fix backend/
