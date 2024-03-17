.PHONY: fmt

fmt:
	-isort .
	-mypy . --check-untyped-defs