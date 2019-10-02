VENV_DIR=venv
VENV_PIP=$(VENV_DIR)/bin/pip3
VENV_PYTHON=$(VENV_DIR)/bin/python3

OPKG_UTILS_GIT="git://git.natinst.com/opkg-utils"
#OPKG_UTILS_GIT="git://git.yoctoproject.org/opkg-utils"
OPKG_UTILS_TAG=0.4.1
OPKG_UTILS_DIR=opkg-utils

FEED_DIR="./build/dist"

.PHONY: dist-feed
dist-feed: clean configure
	$(VENV_PYTHON) fetch-latest-images.py -d $(FEED_DIR)
	chmod --recursive 0554 $(FEED_DIR)/*

$(VENV_DIR):
	virtualenv --python=python3 $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt

$(OPKG_UTILS_DIR):
	git clone $(OPKG_UTILS_GIT) $(OPKG_UTILS_DIR)
	@cd $(OPKG_UTILS_DIR) && git checkout $(OPKG_UTILS_TAG) 1>/dev/null

.PHONY: clean
clean:
	rm -rf ./build

.PHONY: cleanall
cleanall: clean
	rm -rf $(OPKG_UTILS_DIR)
	rm -rf $(VENV_DIR)

.PHONY: configure
configure: $(VENV_DIR) $(OPKG_UTILS_DIR)
