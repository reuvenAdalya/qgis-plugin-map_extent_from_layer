# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 YOUR NAME
"""Compatibility helpers so the same code runs on QGIS 3.42+ (Qt5)
and QGIS 4.x (Qt6), where some enums became strictly scoped."""

from qgis.PyQt.QtCore import Qt
from qgis.core import QgsLayoutObject


def right_dock_area():
    """Qt.RightDockWidgetArea, scoped-safe for Qt6."""
    try:
        return Qt.DockWidgetArea.RightDockWidgetArea
    except AttributeError:
        return Qt.RightDockWidgetArea


def extent_dd_keys():
    """Return the data-defined property keys for a map item's extent
    bounds: (MapXMin, MapYMin, MapXMax, MapYMax)."""
    try:
        ddp = QgsLayoutObject.DataDefinedProperty
        return ddp.MapXMin, ddp.MapYMin, ddp.MapXMax, ddp.MapYMax
    except AttributeError:
        return (
            QgsLayoutObject.MapXMin,
            QgsLayoutObject.MapYMin,
            QgsLayoutObject.MapXMax,
            QgsLayoutObject.MapYMax,
        )


def layer_filters():
    """Vector + Raster filter flags for QgsMapLayerComboBox, or None."""
    try:
        from qgis.core import QgsMapLayerProxyModel
        return QgsMapLayerProxyModel.VectorLayer | QgsMapLayerProxyModel.RasterLayer
    except Exception:
        return None
