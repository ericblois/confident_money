from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


class MarkdownWindow(QtWidgets.QMainWindow):
    """Display a markdown file in a dedicated read-only window."""

    def __init__(
        self,
        markdown_path: str | Path,
        *,
        title: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent, QtCore.Qt.WindowType.Window)
        self._markdown_path = Path(markdown_path)
        self._viewer = QtWidgets.QTextBrowser(self)
        self._viewer.setReadOnly(True)
        self._viewer.setOpenExternalLinks(True)
        self._viewer.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._viewer.setStyleSheet(
            """
            QTextBrowser {
                background: #111827;
                border: none;
                color: #e5e7eb;
                padding: 18px 22px;
                selection-background-color: #1d4ed8;
            }
            """
        )
        self._viewer.document().setDefaultStyleSheet(
            """
            a {
                color: #60a5fa;
                text-decoration: none;
            }
            h1, h2, h3, h4 {
                color: #f8fafc;
            }
            p, li {
                line-height: 1.45;
            }
            pre, code {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: "Menlo", "Courier New", monospace;
            }
            pre {
                padding: 10px;
                border-radius: 6px;
            }
            table {
                border-collapse: collapse;
                margin: 10px 0;
            }
            th, td {
                border: 1px solid #334155;
                padding: 6px 8px;
            }
            th {
                background: #1e293b;
            }
            """
        )

        self.setStyleSheet("QMainWindow { background: #111827; }")
        self.setCentralWidget(self._viewer)
        self.setWindowTitle(title or self._markdown_path.stem.replace("_", " ").title())

        self._resize_for_screen()
        self.reload_markdown()

    def reload_markdown(self) -> None:
        try:
            markdown_text = self._markdown_path.read_text(encoding="utf-8")
        except OSError as exc:
            self._viewer.setHtml(
                (
                    "<h1>Unable to Open Markdown File</h1>"
                    f"<p><b>Path:</b> {self._markdown_path}</p>"
                    f"<p><b>Error:</b> {exc}</p>"
                )
            )
            return

        self._viewer.document().setBaseUrl(
            QtCore.QUrl.fromLocalFile(f"{self._markdown_path.parent}/")
        )
        self._viewer.setMarkdown(markdown_text)
        self._viewer.moveCursor(QtGui.QTextCursor.MoveOperation.Start)

    def _resize_for_screen(self) -> None:
        parent_window = self.parentWidget().window() if self.parentWidget() else None
        window_handle = parent_window.windowHandle() if parent_window else None
        screen = window_handle.screen() if window_handle else QtGui.QGuiApplication.primaryScreen()

        if screen is None:
            self.resize(960, 720)
            return

        available_geometry = screen.availableGeometry()
        width = available_geometry.width() // 2
        height = (available_geometry.height() * 2) // 3
        self.resize(width, height)
        self.move(
            available_geometry.x() + (available_geometry.width() - width) // 2,
            available_geometry.y() + (available_geometry.height() - height) // 2,
        )
