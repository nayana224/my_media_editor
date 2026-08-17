import sys

from PySide6.QtWidgets import QApplication

from media_editor.main_window import MainWindow
from media_editor.style import APP_STYLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Media Editor")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()

    raise SystemExit(app.exec())
