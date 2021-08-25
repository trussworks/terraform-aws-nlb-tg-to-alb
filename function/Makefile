.PHONY: build
build:
	find . -name __pycache__ | rm -rf
	rm -rf .pytest_cache
	rm -f deployment.zip && zip -r -9 deployment.zip .

.PHONY: test
test:
	PYTHONPATH=. pytest
