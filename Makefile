.PHONY: install install-frontend test test-backend test-frontend run cli docker smoke smoke-ui smoke-all smoke-24h deploy-staging deploy-production

install:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

test: test-backend test-frontend

test-backend:
	cd backend && pytest -q

test-frontend:
	cd frontend && npm run lint && npm run build

run:
	cd backend && uvicorn app.workflows.main:create_app --factory --reload --host 0.0.0.0 --port 8000

cli:
	cd backend && python demo_cli.py

docker:
	docker compose up --build

smoke:
	bash infra/smoke_api.sh "$$PUBLIC_BASE_URL" "$$BUYEROS_API_KEY"

smoke-ui:
	cd frontend && npm run ui:smoke

smoke-all:
	bash infra/smoke_full.sh "$$PUBLIC_BASE_URL" "$$BUYEROS_API_KEY" "$$BUYEROS_UI_BASE_URL"

smoke-24h:
	bash infra/smoke_24h.sh "$$PUBLIC_BASE_URL" "$$BUYEROS_API_KEY" "$${BUYEROS_SMOKE_HOURS:-24}" "$${BUYEROS_SMOKE_INTERVAL_SECONDS:-3600}"

deploy-staging:
	bash infra/deploy_and_smoke.sh root@167.172.60.38 /opt/buyeros .env.production.local "$$STAGING_BASE_URL"

deploy-production:
	bash infra/deploy_and_smoke.sh root@206.189.116.155 /opt/buyeros .env.production.local "$$PUBLIC_BASE_URL" --backup-before
