# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 YOUR NAME
"""Main plugin class. Creates one dock per Print Layout designer window and
cleans them up when designers close or the plugin unloads."""

from .extent_link_dock import ExtentLinkDock


class ExtentLinkerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self._docks = {}  # designer -> ExtentLinkDock

    def initGui(self):  # noqa: N802 (QGIS-required name)
        self.iface.layoutDesignerOpened.connect(self._on_designer_opened)
        self.iface.layoutDesignerWillBeClosed.connect(self._on_designer_closed)

    def unload(self):
        try:
            self.iface.layoutDesignerOpened.disconnect(self._on_designer_opened)
        except Exception:
            pass
        try:
            self.iface.layoutDesignerWillBeClosed.disconnect(self._on_designer_closed)
        except Exception:
            pass
        for dock in list(self._docks.values()):
            try:
                dock.cleanup()
            except Exception:
                pass
        self._docks.clear()

    def _on_designer_opened(self, designer):
        if designer in self._docks:
            return
        try:
            self._docks[designer] = ExtentLinkDock(designer, self.iface)
        except Exception as exc:  # never let a UI error block the designer
            try:
                designer.messageBar().pushWarning(
                    "Map Extent From Layer", "Could not initialise: {0}".format(exc)
                )
            except Exception:
                pass

    def _on_designer_closed(self, designer):
        dock = self._docks.pop(designer, None)
        if dock is not None:
            try:
                dock.cleanup()
            except Exception:
                pass
