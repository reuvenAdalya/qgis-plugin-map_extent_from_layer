# QGIS Extent To Layer

A QGIS Print Layout plugin that links a layout map item's **extent** to the
extent of a project layer, with an adjustable percentage buffer. The link is
live, toggleable per map item, and stored natively in the project via
data-defined properties (so it keeps working even without the plugin
installed).

The installable plugin lives in the [`extent_to_layer/`](extent_to_layer/)
folder. See that folder's [README](extent_to_layer/README.md) for full usage
documentation.

## Install (from source)

Copy the `extent_to_layer/` folder into your QGIS profile plugins directory:

- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

Then enable **Extent To Layer** in Plugins ▸ Manage and Install Plugins.

Or build an installable zip (see below) and use *Install from ZIP*.

## Build an installable zip

```bash
zip -r extent_to_layer.zip extent_to_layer -x '*__pycache__*' -x '*.pyc'
```

The zip must contain the `extent_to_layer/` folder at its root.

## Requirements

QGIS 3.42 or newer, including QGIS 4.x (Qt6).

## License

GNU General Public License v2.0 or later (GPL-2.0-or-later). See
[`LICENSE`](LICENSE).
