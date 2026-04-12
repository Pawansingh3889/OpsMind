.PHONY: setup test run seed clean

setup:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v

run:
	streamlit run app.py

seed:
	python scripts/seed_demo_db.py

clean:
	rm -rf data/demo.db __pycache__
