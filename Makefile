.PHONY: setup test run seed clean lint format typecheck typecheck-ty eval eval-library eval-llm

setup:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v --ignore=tests/eval

run:
	streamlit run app.py

seed:
	python scripts/seed_demo_db.py

lint:
	ruff check .

format:
	ruff format .

# Strict local type check — mypy follows all the usual rules.
typecheck:
	mypy modules/

# CI-parity type check — ty runs in .github/workflows/tests.yml as advisory.
# Failures here are informational until the codebase is fully ty-clean; match
# CI by not failing the target on type errors.
typecheck-ty:
	ty check modules/ || true

# Full eval — library path + LLM path. Requires Ollama with gemma3:12b locally.
eval:
	python -m pytest tests/eval/ -v

# Library fast-path only — no Ollama needed, safe to run in CI.
eval-library:
	OPSMIND_EVAL_SKIP_LLM=1 python -m pytest tests/eval/ -v -m eval_library

# LLM path only — iterate on prompts + model choice.
eval-llm:
	python -m pytest tests/eval/ -v -m eval_llm

clean:
	rm -rf data/demo.db __pycache__
