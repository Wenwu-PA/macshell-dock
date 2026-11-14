.PHONY: check install uninstall dist
check:
	python3 tools/check.py
install:
	./install.sh
uninstall:
	./uninstall.sh
dist: check
	python3 tools/package.py
