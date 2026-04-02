.PHONY: setup run test clean seed lint

setup: ## Install dependencies and seed demo database
	pip install -r requirements.txt
	python scripts/seed_demo_db.py
	python scripts/ingest_documents.py

run: ## Start Streamlit app
	streamlit run app.py

test: ## Run pytest test suite
	python -m pytest tests/test_core.py -v

seed: ## Regenerate demo database
	python scripts/seed_demo_db.py
	python scripts/ingest_documents.py

clean: ## Remove generated data files
	rm -f data/demo.db
	rm -rf data/chroma_db

lint: ## Check code style
	python -m py_compile app.py
	python -m py_compile config.py
	@for f in modules/*.py; do python -m py_compile "$$f"; done
	@echo "All files compile successfully"

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
