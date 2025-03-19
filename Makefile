
install:
	@pip install uv
	@uv sync

test:
	@PYTHONPATH=$(PWD) uv run pytest tests

build:
	@PYTHONPATH=$(PWD) uv build

publish:
	@uv publish
