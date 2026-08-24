install:
	python -m pip install -r apps/api/requirements.txt
	cd apps/dashboard && npm install
dev:
	docker compose up --build
test:
	pytest -q
lint:
	ruff check services tests
	cd apps/dashboard && npm run lint
format:
	ruff format services tests
	cd apps/dashboard && npx prettier --write .
