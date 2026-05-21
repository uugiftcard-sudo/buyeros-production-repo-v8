.PHONY: install test run cli docker

install:
	cd backend && pip install -r requirements.txt

test:
	cd backend && pytest -q

run:
	cd backend && uvicorn app.workflows.main:create_app --factory --reload --host 0.0.0.0 --port 8000

cli:
	cd backend && python demo_cli.py

docker:
	docker compose up --build
