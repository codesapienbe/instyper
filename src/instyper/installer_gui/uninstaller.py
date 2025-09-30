import shutil
import threading
import subprocess
from pathlib import Path
import os
import tempfile
import json
from typing import Any

# Import shared symbols from package-level initializer; fall back if not present
try:
    from . import QtWidgets, QtCore, QtGui, write_log, LOG_FILENAME, appdirs
except Exception:
    QtWidgets: Any = None  # type: ignore
    QtCore: Any = None  # type: ignore
    QtGui: Any = None  # type: ignore
    write_log: Any = None  # type: ignore
    LOG_FILENAME = 'application.log'
    appdirs: Any = None


if QtWidgets is not None and QtCore is not None:

    class UninstallerWorker(QtCore.QObject):
        _Signal = getattr(QtCore, 'pyqtSignal', None) or getattr(QtCore, 'Signal', None)
        if _Signal is None:
            class _DummySignal:
                def __init__(self, *a, **k):
                    pass
                def connect(self, *a, **k):
                    pass
                def emit(self, *a, **k):
                    pass
            _Signal = _DummySignal

        progress = _Signal(str)
        finished = _Signal(bool, str)

        def __init__(self, install_dir: str, remove_user_data: bool):
            super().__init__()
            self.install_dir = Path(install_dir).expanduser().resolve()
            self.remove_user_data = bool(remove_user_data)
            # log into install_dir/application.log if possible
            self.log_path = (self.install_dir / LOG_FILENAME) if self.install_dir.exists() else None

        def run(self):
            try:
                self.progress.emit('2:Starting uninstallation')
                if write_log is not None and self.log_path is not None:
                    write_log(self.log_path, 'INFO', 'uninstaller', 'starting', install_dir=str(self.install_dir))

                # Stage: locate
                self.progress.emit('10:Locating installation')
                if not self.install_dir.exists():
                    msg = f'Install directory not found: {self.install_dir}'
                    self.progress.emit(f'stage:locate:fail')
                    if write_log is not None and self.log_path is not None:
                        write_log(self.log_path, 'WARN', 'uninstaller', 'not_found', path=str(self.install_dir))
                    self.finished.emit(False, msg)
                    return
                self.progress.emit('stage:locate:ok')

                # Stage: remove application directory
                self.progress.emit('30:Removing application directory')
                self.progress.emit('stage:remove_app:started')
                try:
                    shutil.rmtree(str(self.install_dir))
                    if write_log is not None and self.log_path is not None:
                        write_log(self.log_path, 'INFO', 'uninstaller', 'removed_app_dir', path=str(self.install_dir))
                    self.progress.emit('stage:remove_app:ok')
                except Exception as e:
                    if write_log is not None and self.log_path is not None:
                        write_log(self.log_path, 'ERROR', 'uninstaller', 'remove_app_failed', error=str(e))
                    self.progress.emit('stage:remove_app:fail')
                    self.finished.emit(False, f'Failed removing application: {e}')
                    return

                # Stage: remove user data
                if self.remove_user_data:
                    self.progress.emit('60:Removing user data')
                    self.progress.emit('stage:remove_user:started')
                    try:
                        if appdirs:
                            user_data = Path(appdirs.user_data_dir('Instyper', appauthor=False))
                        else:
                            user_data = Path.home() / '.instyper'
                        if user_data.exists():
                            # remove safely
                            shutil.rmtree(str(user_data))
                            if write_log is not None and self.log_path is not None:
                                write_log(self.log_path, 'INFO', 'uninstaller', 'removed_user_data', path=str(user_data))
                        self.progress.emit('stage:remove_user:ok')
                    except Exception as e:
                        if write_log is not None and self.log_path is not None:
                            write_log(self.log_path, 'WARN', 'uninstaller', 'remove_user_failed', error=str(e))
                        self.progress.emit('stage:remove_user:fail')
                        # continue; user may clean manually

                # Stage: finished
                self.progress.emit('100:Uninstallation completed')
                if write_log is not None and self.log_path is not None:
                    write_log(self.log_path, 'INFO', 'uninstaller', 'completed')
                self.progress.emit('stage:all:ok')
                self.finished.emit(True, str(self.install_dir))
            except Exception as e:
                if write_log is not None and self.log_path is not None:
                    write_log(self.log_path, 'ERROR', 'uninstaller', 'failed', error=str(e))
                self.finished.emit(False, str(e))


    class UninstallerWindow(QtWidgets.QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('Instyper Uninstaller')
            self.resize(640, 420)

            layout = QtWidgets.QVBoxLayout(self)

            # Welcome card
            try:
                card = QtWidgets.QFrame()
                card.setFrameShape(QtWidgets.QFrame.StyledPanel)
                h = QtWidgets.QHBoxLayout(card)
                icon = QtWidgets.QLabel()
                icon.setFixedSize(80, 80)
                try:
                    from . import find_project_logo
                    logo = find_project_logo()
                    if logo and logo.exists() and QtGui is not None:
                        pix = QtGui.QPixmap(str(logo)).scaled(80, 80, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                        icon.setPixmap(pix)
                except Exception:
                    pass
                h.addWidget(icon)
                ttl = QtWidgets.QLabel('<b><span style="font-size:16pt">Uninstall Instyper</span></b>')
                h.addWidget(ttl)
                layout.addWidget(card)
            except Exception:
                pass

            # Install dir input
            default_dir = appdirs.user_data_dir('Instyper', appauthor=False) if appdirs else str(Path.home())
            self.install_dir_input = QtWidgets.QLineEdit(default_dir)
            layout.addWidget(self.install_dir_input)

            # Remove user data checkbox
            self.remove_user_cb = QtWidgets.QCheckBox('Also remove user data (~/ .instyper)')
            layout.addWidget(self.remove_user_cb)

            # Buttons
            btn_row = QtWidgets.QHBoxLayout()
            self.start_btn = QtWidgets.QPushButton('Uninstall')
            self.start_btn.clicked.connect(self.start_uninstall)
            btn_row.addStretch(1)
            btn_row.addWidget(self.start_btn)
            layout.addLayout(btn_row)

            # Progress and logs
            self.progress_bar = QtWidgets.QProgressBar()
            self.progress_bar.setRange(0, 100)
            try:
                self.progress_bar.setFixedHeight(20)
            except Exception:
                pass
            layout.addWidget(self.progress_bar)

            self.progress_output = QtWidgets.QTextEdit()
            self.progress_output.setReadOnly(True)
            self.progress_output.setVisible(False)
            layout.addWidget(self.progress_output)

            self._log_viewer = QtWidgets.QTextEdit()
            self._log_viewer.setReadOnly(True)
            self._log_viewer.setVisible(False)
            toggle = QtWidgets.QToolButton()
            toggle.setText('See details')
            toggle.setCheckable(True)
            toggle.toggled.connect(lambda c: self._log_viewer.setVisible(c))
            layout.addWidget(toggle)
            layout.addWidget(self._log_viewer)

            self.thread = None
            self.worker = None

        def append_log(self, message: str) -> None:
            try:
                m = __import__('re').match(r"^(\d{1,3}):(.*)$", message)
                if m:
                    pct = int(m.group(1))
                    text = m.group(2).strip()
                    self.progress_bar.setValue(max(0, min(100, pct)))
                    try:
                        self.progress_output.append(f'[{pct}%] {text}')
                    except Exception:
                        pass
                    try:
                        self._log_viewer.moveCursor(QtGui.QTextCursor.End)
                        self._log_viewer.insertPlainText(f'[{pct}%] {text}\n')
                        self._log_viewer.moveCursor(QtGui.QTextCursor.End)
                    except Exception:
                        pass
                    return
                self.progress_output.append(message)
                try:
                    self._log_viewer.moveCursor(QtGui.QTextCursor.End)
                    self._log_viewer.insertPlainText(message + '\n')
                    self._log_viewer.moveCursor(QtGui.QTextCursor.End)
                except Exception:
                    pass
            except Exception:
                pass

        def start_uninstall(self):
            install_dir = self.install_dir_input.text().strip()
            if not install_dir:
                QtWidgets.QMessageBox.warning(self, 'Missing directory', 'Please provide the installation directory to remove.')
                return
            # Confirm destructive action
            ok = QtWidgets.QMessageBox.question(self, 'Confirm Uninstall', f'Remove installation at {install_dir}? This cannot be undone.', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if ok != QtWidgets.QMessageBox.Yes:
                return

            remove_user = self.remove_user_cb.isChecked()

            # disable inputs
            self.install_dir_input.setEnabled(False)
            self.start_btn.setEnabled(False)

            # start worker
            self.thread = QtCore.QThread()
            self.worker = UninstallerWorker(install_dir, remove_user)
            self.worker.moveToThread(self.thread)
            self.worker.progress.connect(self.append_log)
            self.worker.finished.connect(self.on_finished)
            self.thread.started.connect(self.worker.run)
            self.thread.start()

        def on_finished(self, ok: bool, result: str) -> None:
            try:
                try:
                    if getattr(self, 'thread', None) is not None:
                        quit_fn = getattr(self.thread, 'quit', None)
                        if callable(quit_fn):
                            try:
                                quit_fn()
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    self.install_dir_input.setEnabled(True)
                    self.start_btn.setEnabled(True)
                except Exception:
                    pass
                try:
                    self.progress_bar.setValue(100 if ok else self.progress_bar.value())
                except Exception:
                    pass
                try:
                    if ok:
                        QtWidgets.QMessageBox.information(self, 'Uninstall complete', f'Uninstalled: {result}')
                    else:
                        QtWidgets.QMessageBox.critical(self, 'Uninstall failed', f'Uninstall failed: {result}')
                except Exception:
                    pass
            except Exception:
                pass


def main():
    if QtWidgets is None or QtCore is None:
        print('GUI not available; install PySide6 or PyQt5 to run the uninstaller.')
        return 2
    app = QtWidgets.QApplication([])
    w = UninstallerWindow()
    w.show()
    return app.exec_() 