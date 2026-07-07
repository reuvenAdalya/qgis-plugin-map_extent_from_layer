# Map Extent From Layer

A QGIS Print Layout plugin that links a layout map item's **extent** to the
extent of a project layer, with an adjustable percentage buffer. The link is
**live**, **toggleable**, and stored **natively** in the project.

Because the link is implemented with the map item's data-defined extent
properties, it keeps working even for people who open the project without this
plugin installed — the plugin is simply a convenient UI for setting and
clearing those expressions.

## Features

- Link the selected map item's extent to any **vector or raster** layer in the
  project.
- **Buffer** field (percent): `100%` reproduces the exact layer extent, values
  above grow it, values below shrink it — all about the extent's centre.
- **Toggle on/off** per map item. Turning it off freezes the map at its current
  view (keeping the item's frame size) and returns it to manual control.
- **CRS-aware**: when the layer and map CRS differ, a coordinate transform is
  applied automatically.
- For vector sources, the layout preview refreshes automatically when you
  finish an edit session (commit).
- A dockable panel in the Layout Designer whose open/closed state is remembered
  across designers.

## Usage

1. Open a Print Layout and select (or add) a map item.
2. Click the **Map Extent From Layer** button in the layout toolbar to show the panel.
3. Tick **Link extent to layer**, choose a source layer, and set a buffer.
4. The map extent now follows that layer. It re-evaluates on refresh/export, and
   (for vector layers) after each commit.
5. Untick to freeze and return to manual extent control.

## How it works

When enabled, the plugin sets the map item's `MapXMin`, `MapYMin`, `MapXMax`
and `MapYMax` data-defined properties to expressions built from
`layer_property(<layer>, 'extent')`, scaled by the buffer factor and, when
needed, wrapped in `transform(...)` to the map CRS. These expressions are
stored in the project by QGIS itself.

## Requirements

- QGIS 3.42 or newer (tested), including QGIS 4.x (Qt6).

## Notes and limitations

- QGIS fits the final extent to the map frame's aspect ratio, so the displayed
  area may be slightly larger on one axis than the raw layer extent. This is
  normal QGIS behaviour.
- A degenerate (zero-area) layer extent — e.g. a single point — cannot define a
  usable map extent; QGIS reports this and the link has no effect until the
  layer has a non-zero extent.
- If a linked layer is renamed, rebuild the link (re-tick the checkbox) so the
  expression references the new name.

## License

GNU General Public License v2.0 or later (GPL-2.0-or-later). See the `LICENSE`
file.
