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



app:
	uv run --frozen fastapi run ./src/app/main.py

start:
	sudo systemctl start neuraltag.service

stop:
	sudo systemctl stop neuraltag.service

restart:
	sudo systemctl restart neuraltag.service

status:
	sudo systemctl status neuraltag.service

logs:
	journalctl -u neuraltag.service -f -n 300

alembic-revision:
	cd src/database/ && alembic revision --autogenerate -m "current state"

alembic-upgrade:
	cd src/database/ && alembic upgrade head
