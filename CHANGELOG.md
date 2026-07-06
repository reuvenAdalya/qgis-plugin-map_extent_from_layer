# Changelog

All notable changes to this project are documented here.

## [0.1.2]
- Remember the dock's open/closed state across layout designers via QgsSettings,
  with filtering so window minimize/close does not overwrite the preference.

## [0.1.1]
- Fix: disabling a link no longer shrinks the map item's frame. The map is now
  frozen with `zoomToExtent()` (keeps the item size) instead of `setExtent()`.

## [0.1.0]
- Initial release.
- Link a layout map item's extent to a vector or raster layer's extent.
- Percentage buffer (default 100%), CRS-aware transform, per-item on/off toggle.
- Data-defined extent expressions stored natively in the project.
- Automatic preview refresh on vector-layer commit.
