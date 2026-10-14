"""Per-window autosave timer and an on-demand recovery chooser."""

import copy
import os
import uuid
from pathlib import Path

from PySide6 import QtCore as C
from PySide6 import QtWidgets as W

from ..projects import normalize_document
from ..recovery import candidates, write_snapshot


class RecoveryMixin:
    def setup_recovery(self):
        self.recovery_session = uuid.uuid4().hex
        self.recovery_path = None
        override = os.environ.get("PLOTFOLIO_AUTOSAVE_DIR")
        self.recovery_dir = Path(
            override
            or C.QStandardPaths.writableLocation(
                C.QStandardPaths.StandardLocation.AppLocalDataLocation
            )
        ) / ("" if override else "recovery")
        self.autosave_timer = C.QTimer(self)
        self.autosave_timer.setInterval(60000)
        self.autosave_timer.timeout.connect(self.autosave)
        if override or os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            self.autosave_timer.start()
            if candidates(self.recovery_dir):
                C.QTimer.singleShot(0, self.recover_work)

    def autosave(self):
        if not self.dirty:
            return
        try:
            self.recovery_path = write_snapshot(
                self.recovery_dir, self.recovery_session, self.doc, self.filename
            )
        except (OSError, ValueError) as error:
            self.statusBar().showMessage(f"Autosave could not write a recovery snapshot: {error}")

    def clear_recovery(self):
        if self.recovery_path:
            try:
                self.recovery_path.unlink(missing_ok=True)
            except OSError:
                pass
            self.recovery_path = None

    def recover_work(self):
        items = candidates(self.recovery_dir)
        dialog = W.QDialog(self)
        dialog.setWindowTitle("Recover interrupted work")
        dialog.resize(660, 360)
        layout = W.QVBoxLayout(dialog)
        label = W.QLabel(
            "Restore a snapshot as unsaved work, discard it, or close to decide later. Project files are never replaced."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        listing = W.QListWidget()
        layout.addWidget(listing)
        from datetime import datetime

        listing.addItems(
            [
                f"{item['filename'] or 'Untitled figure'} · {datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M')}"
                for _, item in items
            ]
            or ["No interrupted sessions found."]
        )
        row = W.QHBoxLayout()
        layout.addLayout(row)

        def restore():
            index = listing.currentRow()
            if not 0 <= index < len(items):
                return
            try:
                path, item = items[index]
                doc = normalize_document(copy.deepcopy(item["document"]), validate=False)
                if not self.confirm_discard():
                    return
                self.replace_document(doc, item["filename"])
                self.dirty = True
                self.update_title()
                self.autosave()
                path.unlink(missing_ok=True)
                dialog.accept()
            except Exception as error:
                self.error(error)

        def discard():
            index = listing.currentRow()
            if 0 <= index < len(items):
                path, _ = items.pop(index)
                path.unlink(missing_ok=True)
                listing.takeItem(index)

        for text, callback in [
            ("Restore", restore),
            ("Discard selected", discard),
            ("Later", dialog.reject),
        ]:
            button = W.QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        if items:
            listing.setCurrentRow(0)
        dialog.exec()
