#!/bin/bash
# Makefile for biathlon project

# makes virtual environment and dependencies, you can run the project with make run
all:
	if [ ! -d "venv" ]; then \
		make env; \
	fi 
	make deps; \
	make run; \

# runs application
run:
	source venv/bin/activate; \
	python src/biathlon_main.py; \

# sets up virtual environment
env:
	if [ ! -d "venv" ]; then \
		pip3 install virtualenv; \
		python3 -m venv venv; \
	fi

# installs all dependencies
deps: 
	make env; \
	source venv/bin/activate; \
	pip install pyqt5; \
	pip install pyqtgraph; \
	pip install paramiko; \
	pip install ffmpeg-python; \
	pip install opencv-python; \
	pip install pyinstaller==3.3.1; \
	pip install imutils; \
	pip install py2app;\

# installs all dependencies and then makes the single executable app, make sure you have activated the virtual environment first
# Note that this is not currently functional and needs work.
# pyinstaller src/biathlon_main.py --onefile --windowed --ico=assets/icon.ico --name="USBA Data Collection Interface" --debug; 
app:
	if [ ! -d "venv" ]; then \
		pip3 install virtualenv; \
		python3 -m venv venv; \
	fi
	make deps; \
	source venv/bin/activate; \
	python src/setup.py py2app -A --icon assets/icon.ico --optimize -0 --graph --argv-emulation --no-strip;\

# executes single-file application
exec:
	source venv/bin/activate; \
	./dist/biathlon_main.app/Contents/MacOS/biathlon_main; \

# removes everything except the virtual environment and code source files
clean:
	rm -rf stored_data
	rm -rf src/__pycache__
	rm -f demo_simple.log
	rm -rf build
	rm -rf dist
	rm -f src/*.pyc
	rm -rf .eggs

# removes everything except the code source files
scrub:
	make clean
	rm -rf venv

	

