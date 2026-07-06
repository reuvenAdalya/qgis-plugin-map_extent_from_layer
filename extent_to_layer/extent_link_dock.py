# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 YOUR NAME
"""Per-designer dock widget. One instance is created for every open Print
Layout designer. It reflects the currently selected map item and lets the
user link that map's extent to a project layer's extent."""

import json
import os
import functools

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from qgis.core import (
    QgsLayoutItemMap,
    QgsProject,
    QgsProperty,
    QgsSettings,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox

from .compat import extent_dd_keys, layer_filters, right_dock_area
from . import extent_expressions as xe

CONFIG_KEY = "extent_to_layer"
# Global preference (applies to every layout designer) for whether the dock
# should open automatically.
VISIBILITY_KEY = "extent_to_layer/dock_visible"


class ExtentLinkDock(QDockWidget):
    def __init__(self, designer, iface):
        super().__init__("Extent To Layer")
        self.designer = designer
        self.iface = iface
        self._current_map = None
        self._loading = False
        self._closing = False
        # map_item.uuid() -> (layer_id, slot) for connected commit hooks
        self._commit_hooks = {}

        plugin_dir = os.path.dirname(__file__)
        icon = QIcon(os.path.join(plugin_dir, "icon.svg"))

        self._build_ui()
        self.setObjectName("ExtentToLayerDock")

        # Toolbar toggle button inside the designer.
        self._action = None
        toolbar = None
        try:
            toolbar = self.designer.layoutToolbar()
        except Exception:
            toolbar = None
        if toolbar is not None:
            from qgis.PyQt.QtWidgets import QAction
            self._action = QAction(icon, "Extent To Layer", self.designer.window())
            self._action.setCheckable(True)
            self._action.setToolTip("Link the selected map item's extent to a layer")
            self._action.toggled.connect(self.setVisible)
            self.visibilityChanged.connect(self._action.setChecked)
            toolbar.addAction(self._action)

        # Dock the panel, then restore the user's last visibility preference
        # (shared across all layout designers). Connect the persistence slot
        # only after the initial restore so we don't save the restore itself.
        self.designer.addDockWidget(right_dock_area(), self)
        visible = QgsSettings().value(VISIBILITY_KEY, False, type=bool)
        self.setVisible(visible)
        self.visibilityChanged.connect(self._remember_visibility)

        # React to selection changes in the layout.
        self._layout = None
        try:
            self._layout = self.designer.layout()
        except Exception:
            self._layout = None
        if self._layout is not None:
            try:
                self._layout.selectionChanged.connect(self._on_selection_changed)
            except Exception:
                pass

        # Reconnect commit hooks for any map items that were already linked
        # (e.g. when reopening a saved project).
        self._reconnect_existing_hooks()
        self._on_selection_changed()

    # ------------------------------------------------------- visibility ----
    def _remember_visibility(self, visible):
        """Persist the dock's open/closed state, but ignore visibility
        changes that are a side effect of the designer window being closed
        or minimized rather than a deliberate user action."""
        if self._closing:
            return
        try:
            win = self.designer.window()
        except Exception:
            win = None
        if win is not None:
            # Window tearing down or hidden -> not a user toggle.
            if not win.isVisible():
                return
            # Minimize hides docks too; don't overwrite the preference.
            if hasattr(win, "isMinimized") and win.isMinimized():
                return
        QgsSettings().setValue(VISIBILITY_KEY, bool(visible))

    # ---------------------------------------------------------------- UI ----
    def _build_ui(self):
        container = QWidget()
        outer = QVBoxLayout(container)

        self._info = QLabel("Select a map item in the layout.")
        self._info.setWordWrap(True)
        outer.addWidget(self._info)

        form = QFormLayout()

        self.enable_cb = QCheckBox("Link extent to layer")
        self.enable_cb.toggled.connect(self._on_enable_toggled)
        form.addRow(self.enable_cb)

        self.layer_cb = QgsMapLayerComboBox()
        flt = layer_filters()
        if flt is not None:
            self.layer_cb.setFilters(flt)
        self.layer_cb.setAllowEmptyLayer(True)
        self.layer_cb.layerChanged.connect(self._on_param_changed)
        form.addRow("Source layer", self.layer_cb)

        self.buffer_sb = QDoubleSpinBox()
        self.buffer_sb.setRange(1.0, 1000.0)
        self.buffer_sb.setDecimals(1)
        self.buffer_sb.setSingleStep(5.0)
        self.buffer_sb.setValue(100.0)
        self.buffer_sb.setSuffix(" %")
        self.buffer_sb.valueChanged.connect(self._on_param_changed)
        form.addRow("Buffer", self.buffer_sb)

        outer.addLayout(form)

        self.crs_note = QLabel("")
        self.crs_note.setWordWrap(True)
        outer.addWidget(self.crs_note)

        outer.addStretch(1)
        self.setWidget(container)
        self._set_controls_enabled(False)

    def _set_controls_enabled(self, on):
        self.enable_cb.setEnabled(on)
        self.layer_cb.setEnabled(on)
        self.buffer_sb.setEnabled(on)

    # -------------------------------------------------------- selection ----
    def _selected_map(self):
        if self._layout is None:
            return None
        try:
            items = self._layout.selectedLayoutItems()
        except Exception:
            return None
        for it in items:
            if isinstance(it, QgsLayoutItemMap):
                return it
        return None

    def _on_selection_changed(self, *args):
        self._current_map = self._selected_map()
        self._load_from_map()

    def _load_from_map(self):
        self._loading = True
        try:
            m = self._current_map
            if m is None:
                self._info.setText("Select a map item in the layout.")
                self.enable_cb.setChecked(False)
                self.buffer_sb.setValue(100.0)
                self.crs_note.setText("")
                self._set_controls_enabled(False)
                return

            self._set_controls_enabled(True)
            label = m.displayName() if hasattr(m, "displayName") else "map item"
            self._info.setText("Editing: {0}".format(label))

            cfg = self._read_config(m)
            self.enable_cb.setChecked(bool(cfg.get("enabled")))
            self.buffer_sb.setValue(float(cfg.get("buffer_pct", 100.0)))
            layer_id = cfg.get("layer_id")
            layer = QgsProject.instance().mapLayer(layer_id) if layer_id else None
            if layer is not None:
                self.layer_cb.setLayer(layer)
            self._update_crs_note()
        finally:
            self._loading = False

    # ------------------------------------------------------------ events ----
    def _on_enable_toggled(self, checked):
        if self._loading:
            return
        m = self._current_map
        if m is None:
            return
        if checked:
            self._apply(m)
        else:
            self._clear_and_freeze(m)
        self._update_crs_note()

    def _on_param_changed(self, *args):
        if self._loading:
            return
        m = self._current_map
        if m is None:
            return
        if self.enable_cb.isChecked():
            self._apply(m)
        self._update_crs_note()

    # ----------------------------------------------------------- helpers ----
    def _map_crs(self, m):
        crs = m.crs()
        if crs is None or not crs.isValid():
            crs = QgsProject.instance().crs()
        return crs

    def _update_crs_note(self):
        m = self._current_map
        layer = self.layer_cb.currentLayer()
        if m is None or layer is None:
            self.crs_note.setText("")
            return
        lcrs = layer.crs()
        mcrs = self._map_crs(m)
        if lcrs.isValid() and mcrs.isValid() and lcrs != mcrs:
            self.crs_note.setText(
                "CRS differ: layer {0} \u2192 map {1}. A transform is applied "
                "automatically.".format(lcrs.authid(), mcrs.authid())
            )
        else:
            self.crs_note.setText("")

    # ------------------------------------------------------------- apply ----
    def _apply(self, m):
        layer = self.layer_cb.currentLayer()
        if layer is None:
            self._push("Pick a source layer first.", warn=True)
            self.enable_cb.blockSignals(True)
            self.enable_cb.setChecked(False)
            self.enable_cb.blockSignals(False)
            return

        buffer_pct = self.buffer_sb.value()

        ext = layer.extent()
        if ext is None or ext.isEmpty() or ext.width() <= 0 or ext.height() <= 0:
            self._push(
                "Layer '{0}' has no usable 2-D extent (for example a single "
                "point or an empty layer). Pick a layer that covers an area, "
                "or add features to it first.".format(layer.name()),
                warn=True,
            )
            self.enable_cb.blockSignals(True)
            self.enable_cb.setChecked(False)
            self.enable_cb.blockSignals(False)
            return
        mcrs = self._map_crs(m)
        xmin, ymin, xmax, ymax = xe.build_expressions(
            layer.name(),
            layer.crs().authid(),
            mcrs.authid(),
            buffer_pct,
        )

        kx0, ky0, kx1, ky1 = extent_dd_keys()
        props = m.dataDefinedProperties()
        props.setProperty(kx0, QgsProperty.fromExpression(xmin))
        props.setProperty(ky0, QgsProperty.fromExpression(ymin))
        props.setProperty(kx1, QgsProperty.fromExpression(xmax))
        props.setProperty(ky1, QgsProperty.fromExpression(ymax))

        self._write_config(m, True, layer.id(), buffer_pct)
        self._connect_commit_hook(m, layer)
        self._refresh_map(m)

    def _clear_and_freeze(self, m):
        # Freeze at the current linked view, then hand back manual control.
        layer = self.layer_cb.currentLayer()
        if layer is not None:
            rect = xe.compute_extent(layer, self._map_crs(m), self.buffer_sb.value())
            if rect is not None:
                try:
                    # zoomToExtent keeps the map item's frame size fixed;
                    # setExtent would resize the box to the extent's aspect ratio.
                    m.zoomToExtent(rect)
                except Exception:
                    pass

        kx0, ky0, kx1, ky1 = extent_dd_keys()
        props = m.dataDefinedProperties()
        for k in (kx0, ky0, kx1, ky1):
            props.setProperty(k, QgsProperty())  # invalid -> removes override

        layer_id = layer.id() if layer is not None else self._read_config(m).get("layer_id")
        self._write_config(m, False, layer_id, self.buffer_sb.value())
        self._disconnect_commit_hook(m)
        self._refresh_map(m)

    def _refresh_map(self, m):
        try:
            m.invalidateCache()
        except Exception:
            pass
        try:
            m.refresh()
        except Exception:
            pass

    # --------------------------------------------------------- config io ----
    def _read_config(self, m):
        raw = m.customProperty(CONFIG_KEY, "")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _write_config(self, m, enabled, layer_id, buffer_pct):
        cfg = {
            "enabled": bool(enabled),
            "layer_id": layer_id,
            "buffer_pct": float(buffer_pct),
        }
        m.setCustomProperty(CONFIG_KEY, json.dumps(cfg))

    # ------------------------------------------------------ commit hooks ----
    def _connect_commit_hook(self, m, layer):
        # Refresh the preview when a vector source finishes an edit session.
        self._disconnect_commit_hook(m)
        if not isinstance(layer, QgsVectorLayer):
            return
        uuid = m.uuid()
        slot = functools.partial(self._on_layer_committed, uuid)
        try:
            layer.afterCommitChanges.connect(slot)
            self._commit_hooks[uuid] = (layer.id(), slot)
        except Exception:
            pass

    def _disconnect_commit_hook(self, m):
        uuid = m.uuid()
        entry = self._commit_hooks.pop(uuid, None)
        if not entry:
            return
        layer_id, slot = entry
        layer = QgsProject.instance().mapLayer(layer_id)
        if isinstance(layer, QgsVectorLayer):
            try:
                layer.afterCommitChanges.disconnect(slot)
            except Exception:
                pass

    def _on_layer_committed(self, uuid):
        if self._layout is None:
            return
        try:
            item = self._layout.itemByUuid(uuid)
        except Exception:
            item = None
        if item is None:
            # Map item gone; drop the stale hook.
            self._commit_hooks.pop(uuid, None)
            return
        self._refresh_map(item)

    def _reconnect_existing_hooks(self):
        if self._layout is None:
            return
        try:
            items = self._layout.items()
        except Exception:
            return
        for it in items:
            if not isinstance(it, QgsLayoutItemMap):
                continue
            cfg = self._read_config(it)
            if not cfg.get("enabled"):
                continue
            layer = QgsProject.instance().mapLayer(cfg.get("layer_id"))
            if isinstance(layer, QgsVectorLayer):
                self._connect_commit_hook(it, layer)

    def _push(self, text, warn=False):
        try:
            bar = self.designer.messageBar()
            if warn:
                bar.pushWarning("Extent To Layer", text)
            else:
                bar.pushInfo("Extent To Layer", text)
        except Exception:
            pass

    # ----------------------------------------------------------- cleanup ----
    def cleanup(self):
        # Stop persisting visibility while the window tears down.
        self._closing = True
        try:
            self.visibilityChanged.disconnect(self._remember_visibility)
        except Exception:
            pass

        # Disconnect all commit hooks.
        for uuid, (layer_id, slot) in list(self._commit_hooks.items()):
            layer = QgsProject.instance().mapLayer(layer_id)
            if isinstance(layer, QgsVectorLayer):
                try:
                    layer.afterCommitChanges.disconnect(slot)
                except Exception:
                    pass
        self._commit_hooks.clear()

        if self._layout is not None:
            try:
                self._layout.selectionChanged.disconnect(self._on_selection_changed)
            except Exception:
                pass

        if self._action is not None:
            try:
                self._action.toggled.disconnect(self.setVisible)
            except Exception:
                pass
            try:
                self._action.setParent(None)
            except Exception:
                pass
            self._action = None

        try:
            self.designer.removeDockWidget(self)
        except Exception:
            pass
        try:
            self.setParent(None)
        except Exception:
            pass
