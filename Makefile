PYTHON_IMAGE ?= python:3.12-slim
PROJECT_DIR ?= $(CURDIR)
PYTEST_ARGS ?= -q

.PHONY: test test-docker test-docker-verbose

test: test-docker

test-docker:
	docker run --rm -v "$(PROJECT_DIR):/app" -w /app $(PYTHON_IMAGE) sh -lc "pip install --no-cache-dir pytest && PYTHONPATH=/app pytest $(PYTEST_ARGS)"

test-docker-verbose:
	$(MAKE) test-docker PYTEST_ARGS="-vv"
