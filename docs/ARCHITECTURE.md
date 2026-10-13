# Architecture

`app.py` owns Qt startup. `model.py` defines serializable defaults. `data.py` parses CSV and images. `rendering.py` builds figures without Qt; `annotations.py` draws marks. `legends.py` defines legend defaults, placement and shared-entry merging. `projects.py` saves and migrates projects. `examples.py` defines synthetic data. `engine.py` exposes a compatibility API.

`ui/window.py` owns selection, undo/redo and delayed live rendering. `ui/editors.py` binds inspector controls to model fields. `ui/project_actions.py` handles file dialogs and data previews. `ui/widgets.py` and `ui/theme.py` share presentation. `manuscript.py` merges an independently rendered vector PDF at scale 1; `ui/manuscript.py` displays it with Qt PDF.

Figure export always creates a fresh Matplotlib Figure from physical model dimensions. Never export resized canvas geometry. Project version 2 embeds datasets and images; missing fields receive defaults. Keep rendering deterministic and independent of Qt.

Scientific workflows live in Qt-independent modules: `ingestion.py` handles configurable text/Excel import and metadata; `expressions.py` interprets a whitelist of arithmetic AST nodes without evaluating Python; `analysis.py` creates immutable derived tables with operation records and explicit statistics; `fitting.py` uses SciPy least squares with covariance diagnostics; `templates.py` serializes designs without source rows or fitted artifacts and preflights batch exports; `overlays.py` draws fits, replicate points, data zooms and secondary axes.

`ui/workflows.py` exposes menu actions. Import, analysis, template and panel-tools dialogs use `ui/workflow_widgets.py` and the shared application theme. Batch exports use a QThread and bare Matplotlib/Agg figures; the modal dialog prevents competing edits. Tests yield Python execution while polling that worker. All persistent settings are ordinary JSON data. Source tables are shared immutable objects across undo states, so metadata/history updates must produce new datasets. Changing fitted X/Y sources or scale factors clears stale fits. Template application does not reuse fit results or individual replicate overlays.
