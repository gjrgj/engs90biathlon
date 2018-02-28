#!/bin/bash
# Makefile for biathlon project

# runs application, make sure you have activated the virtual environment first and run make app
run:
	python src/biathlon_main.py

# sets up virtual environment
env:
	pip3 install virtualenv; \
	python3 -m venv venv; \
	source venv/bin/activate; \

# installs all dependencies
deps: 
	pip install pyqtgraph
	pip install PyQt5
	pip install paramiko
	pip install pyobjc
	# pip install opencv-python==3.1.0.4
	pip install opencv-python
	pip install pyinstaller==3.3.1

# installs all dependencies and then makes the app, make sure you have activated the virtual environment first
app:
	make deps
	pyinstaller src/biathlon_main.py --windowed

# removes everything except the virtual environment and code source files
clean:
	rm -rf stored_data
	rm -rf src/__pycache__
	rm -f demo_simple.log
	rm -rf build
	rm -rf dist
	rm -f src/*.pyc
	rm -f biathlon_main.spec
	rm -rf .eggs

# removes everything except the code source files
scrub:
	make clean
	rm -rf venv

	

