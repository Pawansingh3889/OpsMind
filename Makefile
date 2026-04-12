.PHONY: setup test run seed clean lint format typecheck

setup:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v

run:
	streamlit run app.py

seed:
	python scripts/seed_demo_db.py

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy modules/

clean:
	rm -rf data/demo.db __pycache__
