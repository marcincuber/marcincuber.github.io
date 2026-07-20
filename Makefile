.PHONY: build validate test serve

PYTHON ?= python3

build:
	$(PYTHON) -m portfolio_site build --output dist

validate:
	$(PYTHON) -m portfolio_site validate

test:
	PYTHONPYCACHEPREFIX=/tmp/marcincuber-portfolio-pycache $(PYTHON) -m unittest discover -s tests -v

serve: build
	$(PYTHON) -m portfolio_site serve --output dist --port 8000
