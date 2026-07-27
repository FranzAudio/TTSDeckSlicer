.PHONY: all clean run dev venv test lint build build-alias sign dmg

# Python virtual environment
VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
PYTHON_BOOTSTRAP ?= $(shell command -v python3.11 2>/dev/null || command -v python3)

# Application metadata
APP_NAME = TTS Deck Slicer
VERSION = 1.5.0

all: venv clean build sign dmg

venv:
	@test -d $(VENV) || "$(PYTHON_BOOTSTRAP)" -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install "setuptools<81" "wheel<0.45"
	$(PIP) install -r requirements-dev.txt

clean:
	rm -rf build dist *.spec *.egg-info __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

run: venv
	$(PYTHON) TTSDeckSlicer.py

dev: venv
	PYTHONPATH=. $(PYTHON) TTSDeckSlicer.py

test: venv
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest -q

lint: venv
	$(PYTHON) -m ruff check .

build: venv
	$(PYTHON) setup.py py2app

build-alias: venv
	$(PYTHON) setup.py py2app -A

sign:
	codesign --force --deep --sign - "dist/$(APP_NAME).app"

dmg:
	hdiutil create -volname "$(APP_NAME)" -srcfolder "dist/$(APP_NAME).app" \
		-ov -format UDZO "dist/$(APP_NAME)-$(VERSION).dmg"
