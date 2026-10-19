.PHONY: build validate test serve sync-medium check-links check-live

PYTHON ?= python3.14

sync-medium:
	$(PYTHON) -m portfolio_site sync-medium

check-links: build
	$(PYTHON) -m portfolio_site check-links

check-live: build
	$(PYTHON) -m portfolio_site check-live

build:
	$(PYTHON) -m portfolio_site build --output dist

validate:
	$(PYTHON) -m portfolio_site validate

test:
	PYTHONPYCACHEPREFIX=/tmp/marcincuber-portfolio-pycache $(PYTHON) -m unittest discover -s tests -v

serve: build
	$(PYTHON) -m portfolio_site serve --output dist --port 8000
