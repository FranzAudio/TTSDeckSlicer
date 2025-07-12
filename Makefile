all:
	python3 setup.py py2app

clean:
	rm -rf build dist *.spec