# Compile the Qt resources (icons) into the plugin resources module.
# The import is rewritten to qgis.PyQt so the module is compatible with
# both QGIS 3 (PyQt5) and QGIS 4 (PyQt6).

QRC = resources.qrc
RESOURCES = ../resources.py

resources: $(RESOURCES)

$(RESOURCES): $(QRC) $(wildcard *.svg *.png)
	pyrcc5 $(QRC) -o $(RESOURCES)
	sed -i 's/^from PyQt5 import QtCore$$/from qgis.PyQt import QtCore/' $(RESOURCES)

.PHONY: resources
