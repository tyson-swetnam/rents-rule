# Convenience targets. `make venv` builds a local virtualenv with uv (fast) or pip.
PY ?= python3
VENV ?= .venv

.PHONY: venv test lint demo clean

venv:
	@if command -v uv >/dev/null 2>&1; then \
		uv venv $(VENV) --python 3.12 && uv pip install --python $(VENV)/bin/python -e ".[dev,plot]"; \
	else \
		$(PY) -m venv $(VENV) && $(VENV)/bin/pip install -e ".[dev,plot]"; \
	fi

test:
	$(VENV)/bin/python -m pytest

lint:
	$(VENV)/bin/ruff check src tests

# Runs the whole analysis pipeline on synthetic data (no hardware needed).
demo:
	$(VENV)/bin/rentscale demo

clean:
	rm -rf $(VENV) build dist *.egg-info src/*.egg-info .pytest_cache .ruff_cache
