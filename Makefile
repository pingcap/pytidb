.PHONY: install
install:
	@pip install uv
	@uv sync

.PHONY: install_dev
install_dev:
	@uv sync --all-extras --dev

.PHONY: lint
lint:
	@PYTHONPATH=$(PWD) uv tool run ruff check

.PHONY: format
format:
	@PYTHONPATH=$(PWD) uv tool run ruff format

.PHONY: test
test:
	@PYTHONPATH=$(PWD) uv run pytest tests

.PHONY: build
build:
	@PYTHONPATH=$(PWD) uv build

.PHONY: publish
publish:
	@uv publish
