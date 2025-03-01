all: format lint_tests unit_tests

format:
	ruff check --fix src tests
	ruff format ./src tests

lint_tests:
	ruff check src tests

unit_tests:
	coverage run -m --source src pytest --durations=0
	coverage report -m
	coverage xml


docker-run:
	docker-compose run strava

docker-bash:
	docker-compose run strava bash

deploy:
	bash ./cicd/deploy/deploy.sh