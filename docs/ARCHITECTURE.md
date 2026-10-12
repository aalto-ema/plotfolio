# Architecture

`app.py` owns Qt startup. `model.py` defines serializable defaults. `data.py` parses CSV and images. `rendering.py` builds figures without Qt; `annotations.py` draws marks. `legends.py` defines legend defaults, placement and shared-entry merging. `projects.py` saves and migrates projects. `examples.py` defines synthetic data. `engine.py` exposes a compatibility API.

`ui/window.py` owns selection, undo/redo and delayed live rendering. `ui/editors.py` binds inspector controls to model fields. `ui/project_actions.py` handles file dialogs and data previews. `ui/widgets.py` and `ui/theme.py` share presentation. `manuscript.py` merges an independently rendered vector PDF at scale 1; `ui/manuscript.py` displays it with Qt PDF.

Figure export always creates a fresh Matplotlib Figure from physical model dimensions. Never export resized canvas geometry. Project version 2 embeds datasets and images; missing fields receive defaults. Keep rendering deterministic and independent of Qt.
