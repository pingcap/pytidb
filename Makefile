
install:
	@pip install uv
	@uv sync

install_dev:
	@uv sync --all-extras --dev

lint:
	@PYTHONPATH=$(PWD) uv tool run ruff check

format:
	@PYTHONPATH=$(PWD) uv tool run ruff format

test:
	@PYTHONPATH=$(PWD) uv run pytest tests

build:
	@PYTHONPATH=$(PWD) uv build

publish:
	@uv publish
