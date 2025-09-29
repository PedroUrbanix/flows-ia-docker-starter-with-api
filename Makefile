SHELL := /bin/bash

.PHONY: build up down sh run lint format api

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

sh:
	docker compose run --rm app bash

run:
	docker compose run --rm app python -m cli run --city "$(CITY)" --uf "$(UF)" --all

api:
	docker compose up -d api

lint:
	docker compose run --rm app black --check src

format:
	docker compose run --rm app black src && docker compose run --rm app isort src