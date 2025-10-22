.PHONY: all clean run dev venv test build sign dmg

# Python virtual environment
VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

# Application metadata
APP_NAME = "TTS Deck Slicer"
VERSION = 1.1

all: venv clean build sign dmg

venv:
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install "setuptools<81" "wheel<0.45"
	$(PIP) install -e .

clean:
	rm -rf build dist *.spec *.egg-info __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

run: venv
	$(PYTHON) TTSDeckSlicer.py

dev: venv
	PYTHONPATH=. $(PYTHON) TTSDeckSlicer.py

test: venv
	$(PYTHON) -m pytest tests/

build: venv
	$(PYTHON) setup.py py2app -A

sign:
	codesign --force --deep --sign - "dist/$(APP_NAME).app"

dmg:
	hdiutil create -volname "$(APP_NAME)" -srcfolder dist/$(APP_NAME).app \
		-ov -format UDZO "dist/$(APP_NAME)-$(VERSION).dmg"