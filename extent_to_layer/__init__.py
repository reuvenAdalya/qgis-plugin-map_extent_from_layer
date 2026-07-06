# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 YOUR NAME
"""Extent To Layer - QGIS plugin entry point."""


def classFactory(iface):  # noqa: N802 (QGIS-required name)
    from .extent_linker import ExtentLinkerPlugin
    return ExtentLinkerPlugin(iface)
