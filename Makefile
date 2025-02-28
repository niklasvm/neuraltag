all: format lint_tests unit_tests

format:
	ruff check --fix src tests
	ruff format ./src tests

lint_tests:
	ruff check src tests

unit_tests:
	coverage run -m --source src pytest --durations=0
	coverage report -m


docker-build:
	docker build . -t ghcr.io/niklasvm/strava:latest

docker-run:
	docker run -it --rm ghcr.io/niklasvm/strava:latest

docker-bash:
	docker run -it --rm ghcr.io/niklasvm/strava:latest bash