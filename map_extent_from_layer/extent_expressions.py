# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 YOUR NAME
"""Builds the data-defined extent expressions and computes the equivalent
extent in Python (used when freezing a map on toggle-off)."""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
)


def _esc(text):
    """Escape single quotes for use inside an expression string literal."""
    return (text or "").replace("'", "''")


def _fmt(value):
    """Format a float for embedding in an expression."""
    return ("%g" % float(value))


def _source_extent_expr(layer_name, layer_authid, map_authid):
    """Expression returning the layer's extent geometry, transformed to the
    map's CRS when the two differ."""
    name = _esc(layer_name)
    base = "layer_property('{n}', 'extent')".format(n=name)
    if layer_authid and map_authid and layer_authid != map_authid:
        return "transform({base}, '{s}', '{d}')".format(
            base=base, s=_esc(layer_authid), d=_esc(map_authid)
        )
    return base


def build_expressions(layer_name, layer_authid, map_authid, buffer_pct):
    """Return (xmin, ymin, xmax, ymax) expression strings.

    Each bound is computed about the centre of the source extent and scaled
    by the buffer factor, so 100% reproduces the exact extent, >100% grows
    it and <100% shrinks it.
    """
    ext = _source_extent_expr(layer_name, layer_authid, map_authid)
    f = _fmt(buffer_pct / 100.0)

    def bound(lo, hi, sign):
        # centre +/- half-span * factor
        return (
            "with_variable('e', {ext}, "
            "({lo}(@e) + {hi}(@e)) / 2 {sign} "
            "({hi}(@e) - {lo}(@e)) / 2 * {f})"
        ).format(ext=ext, lo=lo, hi=hi, sign=sign, f=f)

    xmin = bound("x_min", "x_max", "-")
    xmax = bound("x_min", "x_max", "+")
    ymin = bound("y_min", "y_max", "-")
    ymax = bound("y_min", "y_max", "+")
    return xmin, ymin, xmax, ymax


def compute_extent(layer, map_crs, buffer_pct):
    """Compute the same buffered, CRS-transformed extent in Python.

    Returns a QgsRectangle in the map's CRS, or None if it cannot be built.
    """
    if layer is None:
        return None
    rect = layer.extent()
    if rect is None or rect.isEmpty():
        return None

    src_crs = layer.crs()
    if (
        src_crs is not None
        and src_crs.isValid()
        and map_crs is not None
        and map_crs.isValid()
        and src_crs != map_crs
    ):
        try:
            tr = QgsCoordinateTransform(src_crs, map_crs, QgsProject.instance())
            rect = tr.transformBoundingBox(rect)
        except Exception:
            return None

    f = buffer_pct / 100.0
    cx = (rect.xMinimum() + rect.xMaximum()) / 2.0
    cy = (rect.yMinimum() + rect.yMaximum()) / 2.0
    hw = rect.width() / 2.0 * f
    hh = rect.height() / 2.0 * f
    return QgsRectangle(cx - hw, cy - hh, cx + hw, cy + hh)
