all: format lint_tests unit_tests

format:
	ruff check --fix ./
	ruff format ./

lint_tests:
	ruff check src tests

unit_tests:
	coverage run -m --source src pytest --durations=0 ./tests
	coverage report -m
	coverage xml


docker-run:
	source .env && \
	uv pip compile pyproject.toml -o requirements.txt && \
	docker-compose up --build

docker-build:
	source .env && \
	uv pip compile pyproject.toml -o requirements.txt && \
	docker-compose build

docker-bash:
	docker-compose run strava bash

docker-dev:
	docker-compose run strava fastapi dev ./src/app.py --reload --host 0.0.0.0 --port 8000

deploy:
	uv run python cicd/deploy/modify_pyproject_toml.py
	bash ./cicd/deploy/deploy.sh
	git checkout pyproject.toml

on:
	sudo systemctl start strava.service
	sudo systemctl start nginx

off:
	sudo systemctl stop strava.service
	sudo systemctl stop nginx

app:
	fastapi run ./src/app/main.py

logs:
	journalctl -u strava.service -f -n 300

alembic-revision:
	cd src/database/ && alembic revision --autogenerate -m "current state"

alembic-upgrade:
	cd src/database/ && alembic upgrade head
