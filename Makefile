.PHONY: fmt

fmt:
	-isort .
	-ruff --fix .
	-mypy . --check-untyped-defs --strict