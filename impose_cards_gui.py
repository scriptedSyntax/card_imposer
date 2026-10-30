from __future__ import annotations

import sys
from pathlib import Path

from pypdf import PdfReader
from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from impose_cards import PAGE_SIZES_PT, compute_grid, impose_cards, mm_to_pt

BACK_TRANSFORMS = [
    "none",
    "rotate180",
    "mirrorX",
    "mirrorY",
    "mirrorX_rotate180",
    "mirrorY_rotate180",
]


class PreviewWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(320)
        self._positions: list[tuple[float, float]] = []
        self._card_w = 0.0
        self._card_h = 0.0
        self._page_w = PAGE_SIZES_PT["A4"][0]
        self._page_h = PAGE_SIZES_PT["A4"][1]
        self._status = "No preview yet."

    def set_preview(
        self,
        positions: list[tuple[float, float]],
        card_w: float,
        card_h: float,
        page_w: float,
        page_h: float,
        status: str,
    ) -> None:
        self._positions = positions
        self._card_w = card_w
        self._card_h = card_h
        self._page_w = page_w
        self._page_h = page_h
        self._status = status
        self.update()

    def clear_preview(self, status: str) -> None:
        self._positions = []
        self._card_w = 0.0
        self._card_h = 0.0
        self._status = status
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#ffffff"))

        pad = 14
        inner = QRectF(pad, pad, self.width() - 2 * pad, self.height() - 2 * pad)
        if inner.width() < 20 or inner.height() < 20:
            return

        p.setPen(QPen(QColor("#666666"), 2))
        p.drawRect(inner)
        p.setPen(QPen(QColor("#333333"), 1))
        p.drawText(QPointF(inner.left() + 6, inner.top() + 16), "Page preview")

        if self._positions and self._card_w > 0 and self._card_h > 0 and self._page_w > 0 and self._page_h > 0:
            sx = inner.width() / self._page_w
            sy = inner.height() / self._page_h
            p.setPen(QPen(QColor("#1f6feb"), 1))
            for x, y in self._positions:
                rx0 = inner.left() + x * sx
                ry0 = inner.bottom() - (y + self._card_h) * sy
                rw = self._card_w * sx
                rh = self._card_h * sy
                p.drawRect(QRectF(rx0, ry0, rw, rh))

        p.setPen(QPen(QColor("#333333"), 1))
        p.drawText(QPointF(inner.left() + 6, inner.bottom() - 6), self._status)


class InstructionsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Instructions")
        self.resize(640, 520)
        layout = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Card Imposer Instructions\n"
            "++++++++++++++++++++++++++++\n\n"
            "What this tool does\n"
            "- Takes a 2-page card PDF:\n"
            "  Page 1 = Front\n"
            "  Page 2 = Back\n"
            "- Creates a print-ready sheet with repeated cards.\n"
            "- Front and back positions are aligned for duplex printing.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Required file format\n"
            "- Input must be exactly 2 pages.\n"
            "- If not 2 pages, preview/generate will stop with an error.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Top controls\n"
            "- Card PDF (2 pages): Select your source card PDF.\n"
            "- Save as (optional): Choose custom output filename/location.\n"
            "- If empty, output is auto-named next to the input file.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Print size dropdown (Print size)\n"
            "- A3: 297 x 420 mm\n"
            "- A4: 210 x 297 mm\n"
            "- A5: 148 x 210 mm\n"
            "- LETTER: 8.5 x 11 in\n"
            "- LEGAL: 8.5 x 14 in\n"
            "- CUSTOM: Enter your own width/height in mm.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Custom size fields\n"
            "- Custom width (mm): Used only when Print size = CUSTOM.\n"
            "- Custom height (mm): Used only when Print size = CUSTOM.\n"
            "- Both values must be greater than 0.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Layout controls\n"
            "- Margin (mm): Empty border from sheet edge.\n"
            "- Gap (mm): Space between cards.\n"
            "- Scale (%): Card resize before placement.\n"
            "  100 = original size, 120 = larger, 80 = smaller.\n"
            "- Rows (optional): Fixed number of rows.\n"
            "- Columns (optional): Fixed number of columns.\n"
            "- Leave Rows/Columns empty for automatic max fit.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Back side option dropdown\n"
            "- none: No back-page transform.\n"
            "- rotate180: Rotate each back card 180 degrees.\n"
            "- mirrorX: Mirror back card left-to-right.\n"
            "- mirrorY: Mirror back card top-to-bottom.\n"
            "- mirrorX_rotate180: MirrorX then rotate 180.\n"
            "- mirrorY_rotate180: MirrorY then rotate 180.\n"
            "- Use these when duplex front/back orientation is wrong.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Checkboxes\n"
            "- Crop marks: Adds cut guide marks around cards.\n"
            "- Test-sheet labels (F/B): Adds tiny F on front page and B on back page.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Buttons\n"
            "- Preview Layout: Required before creating final PDF.\n"
            "- Create Print PDF: Generates final output using current settings.\n"
            "- Portfolio/GitHub: Opens external links.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Recommended workflow\n"
            "1) Select Card PDF.\n"
            "2) Choose Print size (and custom mm if needed).\n"
            "3) Set Margin, Gap, Scale.\n"
            "4) Click Preview Layout.\n"
            "5) If preview looks right, click Create Print PDF.\n"
            "6) On success, choose Open File or Cancel.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Print dialog settings\n"
            "- Print at Actual size / 100%.\n"
            "- Disable Fit to page / Shrink to fit.\n"
            "- For duplex, test one sheet first before bulk printing.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "Troubleshooting\n"
            "- 'must have exactly 2 pages': input file format is incorrect.\n"
            "- 'cannot fit': reduce Scale, reduce Margin/Gap, or use larger Print size.\n"
            "- Back side upside down/mirrored: change Back side option and test again.\n\n"
            "++++++++++++++++++++++++++++\n\n"
            "By Sam | Scripted Syntax\n"
            "Portfolio: https://scriptedsyntax.github.io/portfolio/\n"
            "GitHub: https://github.com/scriptedsyntax\n\n"
            "Support + Project Inquiries: 0799594621\n"
            "Tip line, coffee line, and collab line in one."
        )
        layout.addWidget(text)


class GenerateWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, kwargs: dict):
        super().__init__()
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            result = impose_cards(**self.kwargs)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Card Imposer - By Sam | Scripted Syntax")
        self.resize(1160, 780)
        self.preview_valid = False
        self._set_window_icon()

        self.input_pdf = QLineEdit()
        self.output_pdf = QLineEdit()
        self.page_size = QComboBox()
        self.page_size.addItems(["A4", "A3", "A5", "LETTER", "LEGAL", "CUSTOM"])
        self.page_width_mm = QLineEdit()
        self.page_height_mm = QLineEdit()
        self.margin_mm = QLineEdit("5")
        self.gap_mm = QLineEdit("3")
        self.scale_percent = QLineEdit("100")
        self.rows = QLineEdit()
        self.cols = QLineEdit()
        self.crop_marks = QCheckBox("Crop marks")
        self.test_sheet = QCheckBox("Test-sheet labels (F/B)")
        self.back_transform = QComboBox()
        self.back_transform.addItems(BACK_TRANSFORMS)

        self.preview = PreviewWidget()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.generate_btn = QPushButton("Create Print PDF")
        self.preview_btn = QPushButton("Preview Layout")
        self.progress: QProgressDialog | None = None
        self.worker_thread: QThread | None = None
        self.worker: GenerateWorker | None = None

        self._build_ui()
        self._wire_invalidation()
        self._on_page_size_changed(self.page_size.currentText())

    def _app_base_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    def _default_output_path(self, input_pdf: Path) -> Path:
        outputs_dir = self._app_base_dir() / "outputs"
        return outputs_dir / f"{input_pdf.stem}_imposed.pdf"

    def _set_window_icon(self) -> None:
        base = self._app_base_dir()
        candidates = [
            base / "assets" / "project_icon.ico",
            base / "assets" / "project_icon.png",
            base / "project_icon.ico",
            base / "project_icon.png",
        ]
        for p in candidates:
            if p.exists():
                self.setWindowIcon(QIcon(str(p)))
                return

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        header = QHBoxLayout()
        title = QLabel("Card Imposer")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)
        ins_btn = QPushButton("Instructions")
        ins_btn.clicked.connect(self.show_instructions)
        header.addWidget(ins_btn)
        port_btn = QPushButton("Portfolio")
        port_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://scriptedsyntax.github.io/portfolio/"))
        )
        header.addWidget(port_btn)
        gh_btn = QPushButton("GitHub")
        gh_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/scriptedsyntax")))
        header.addWidget(gh_btn)
        outer.addLayout(header)

        mid = QHBoxLayout()
        outer.addLayout(mid, stretch=1)

        controls = QGroupBox("Print Setup")
        grid = QGridLayout(controls)
        r = 0

        grid.addWidget(QLabel("Card PDF (2 pages)"), r, 0)
        grid.addWidget(self.input_pdf, r, 1, 1, 3)
        b1 = QPushButton("Browse")
        b1.clicked.connect(self.pick_input)
        grid.addWidget(b1, r, 4)
        r += 1

        grid.addWidget(QLabel("Save as (optional)"), r, 0)
        grid.addWidget(self.output_pdf, r, 1, 1, 3)
        b2 = QPushButton("Save As")
        b2.clicked.connect(self.pick_output)
        grid.addWidget(b2, r, 4)
        r += 1

        grid.addWidget(QLabel("Print size"), r, 0)
        grid.addWidget(self.page_size, r, 1)
        grid.addWidget(QLabel("Custom width (mm)"), r, 2)
        grid.addWidget(self.page_width_mm, r, 3)
        grid.addWidget(QLabel("Custom height (mm)"), r, 4)
        grid.addWidget(self.page_height_mm, r, 5)
        r += 1

        grid.addWidget(QLabel("Margin (mm)"), r, 0)
        grid.addWidget(self.margin_mm, r, 1)
        grid.addWidget(QLabel("Gap (mm)"), r, 2)
        grid.addWidget(self.gap_mm, r, 3)
        grid.addWidget(QLabel("Scale (%)"), r, 4)
        grid.addWidget(self.scale_percent, r, 5)
        r += 1

        grid.addWidget(QLabel("Rows (optional)"), r, 0)
        grid.addWidget(self.rows, r, 1)
        grid.addWidget(QLabel("Columns (optional)"), r, 2)
        grid.addWidget(self.cols, r, 3)
        self.preview_btn.clicked.connect(self.preview_layout)
        grid.addWidget(self.preview_btn, r, 4, 1, 2)
        r += 1

        grid.addWidget(self.crop_marks, r, 0, 1, 2)
        grid.addWidget(self.test_sheet, r, 2, 1, 2)
        grid.addWidget(QLabel("Back side option"), r, 4)
        grid.addWidget(self.back_transform, r, 5)
        r += 1

        self.generate_btn.clicked.connect(self.run_imposer)
        grid.addWidget(self.generate_btn, r, 0, 1, 6)

        left = QVBoxLayout()
        left.addWidget(controls)
        left.addWidget(QLabel("Status"))
        left.addWidget(self.log, stretch=1)
        mid.addLayout(left, stretch=2)

        right = QVBoxLayout()
        right.addWidget(QLabel("Preview (required before create)"))
        pf = QFrame()
        pf.setFrameShape(QFrame.Shape.StyledPanel)
        p_layout = QVBoxLayout(pf)
        p_layout.addWidget(self.preview)
        right.addWidget(pf, stretch=1)
        mid.addLayout(right, stretch=1)

        footer = QLabel(
            "By Sam | Scripted Syntax | Support + Project Inquiries: 0799594621"
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignLeft)
        outer.addWidget(footer)

    def _wire_invalidation(self) -> None:
        for w in [
            self.input_pdf,
            self.output_pdf,
            self.page_width_mm,
            self.page_height_mm,
            self.margin_mm,
            self.gap_mm,
            self.scale_percent,
            self.rows,
            self.cols,
        ]:
            w.textChanged.connect(self.invalidate_preview)
        for w in [self.page_size, self.back_transform]:
            w.currentTextChanged.connect(self.invalidate_preview)
        for w in [self.crop_marks, self.test_sheet]:
            w.stateChanged.connect(self.invalidate_preview)
        self.page_size.currentTextChanged.connect(self._on_page_size_changed)

    def _on_page_size_changed(self, value: str) -> None:
        is_custom = value == "CUSTOM"
        self.page_width_mm.setEnabled(is_custom)
        self.page_height_mm.setEnabled(is_custom)
        self.invalidate_preview()

    def invalidate_preview(self, *_args) -> None:
        self.preview_valid = False
        self.preview.clear_preview("Settings changed. Click Preview Layout before creating.")

    def show_instructions(self) -> None:
        InstructionsDialog(self).exec()

    def pick_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select 2-page PDF", str(Path.cwd()), "PDF Files (*.pdf)")
        if not path:
            return
        src = Path(path)
        self.input_pdf.setText(str(src))
        self.output_pdf.setText(str(self._default_output_path(src)))
        self.preview_layout()

    def pick_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save print PDF", str(Path.cwd()), "PDF Files (*.pdf)")
        if path:
            self.output_pdf.setText(path)

    def _parse_float(self, text: str, field: str) -> float:
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(f"{field} must be a number.") from exc

    def _parse_optional_int(self, text: str, field: str) -> int | None:
        t = text.strip()
        if not t:
            return None
        try:
            return int(t)
        except ValueError as exc:
            raise ValueError(f"{field} must be an integer.") from exc

    def _resolve_page_pt_from_ui(self) -> tuple[float, float, float | None, float | None]:
        size = self.page_size.currentText()
        if size == "CUSTOM":
            w_mm = self._parse_float(self.page_width_mm.text().strip(), "Custom width (mm)")
            h_mm = self._parse_float(self.page_height_mm.text().strip(), "Custom height (mm)")
            if w_mm <= 0 or h_mm <= 0:
                raise ValueError("Custom width/height must be greater than 0.")
            return mm_to_pt(w_mm), mm_to_pt(h_mm), w_mm, h_mm
        w_pt, h_pt = PAGE_SIZES_PT[size]
        return w_pt, h_pt, None, None

    def preview_layout(self) -> None:
        self.log.clear()
        try:
            input_pdf = self.input_pdf.text().strip()
            if not input_pdf:
                raise ValueError("Please choose your card PDF first.")
            p = Path(input_pdf)
            if not p.exists():
                raise FileNotFoundError(f"Input file not found: {p}")

            reader = PdfReader(str(p))
            if len(reader.pages) != 2:
                raise ValueError(f"This file must have exactly 2 pages. Found {len(reader.pages)}.")

            source_w = float(reader.pages[0].mediabox.width)
            source_h = float(reader.pages[0].mediabox.height)
            margin = self._parse_float(self.margin_mm.text().strip(), "Margin (mm)")
            gap = self._parse_float(self.gap_mm.text().strip(), "Gap (mm)")
            scale_percent = self._parse_float(self.scale_percent.text().strip(), "Scale (%)")
            if scale_percent <= 0:
                raise ValueError("Scale (%) must be greater than 0.")

            rows = self._parse_optional_int(self.rows.text(), "Rows")
            cols = self._parse_optional_int(self.cols.text(), "Cols")
            page_w_pt, page_h_pt, _w_mm, _h_mm = self._resolve_page_pt_from_ui()

            grid = compute_grid(
                card_w_pt=source_w * (scale_percent / 100.0),
                card_h_pt=source_h * (scale_percent / 100.0),
                page_w_pt=page_w_pt,
                page_h_pt=page_h_pt,
                margin_pt=mm_to_pt(margin),
                gap_pt=mm_to_pt(gap),
                rows=rows,
                cols=cols,
            )
            status = (
                f"{grid.rows} rows x {grid.cols} columns, {len(grid.positions)} per page, "
                f"Scale {scale_percent:.1f}%, Size {self.page_size.currentText()}"
            )
            self.preview.set_preview(
                positions=grid.positions,
                card_w=grid.card_width_pt,
                card_h=grid.card_height_pt,
                page_w=page_w_pt,
                page_h=page_h_pt,
                status=status,
            )
            self.preview_valid = True
            self.log.append("Preview ready.")
        except Exception as exc:
            self.preview_valid = False
            self.preview.clear_preview(f"Preview error: {exc}")
            QMessageBox.critical(self, "Preview problem", str(exc))

    def run_imposer(self) -> None:
        if not self.preview_valid:
            QMessageBox.warning(self, "Preview needed", "Please click Preview Layout first.")
            return
        try:
            input_path = Path(self.input_pdf.text().strip())
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")
            output_path = (
                Path(self.output_pdf.text().strip())
                if self.output_pdf.text().strip()
                else self._default_output_path(input_path)
            )

            _page_w_pt, _page_h_pt, page_w_mm, page_h_mm = self._resolve_page_pt_from_ui()
            kwargs = {
                "input_path": input_path,
                "output_path": output_path,
                "page_size": self.page_size.currentText(),
                "page_width_mm": page_w_mm,
                "page_height_mm": page_h_mm,
                "margin_mm": self._parse_float(self.margin_mm.text().strip(), "Margin (mm)"),
                "gap_mm": self._parse_float(self.gap_mm.text().strip(), "Gap (mm)"),
                "rows": self._parse_optional_int(self.rows.text(), "Rows"),
                "cols": self._parse_optional_int(self.cols.text(), "Cols"),
                "scale_percent": self._parse_float(self.scale_percent.text().strip(), "Scale (%)"),
                "crop_marks": self.crop_marks.isChecked(),
                "test_sheet": self.test_sheet.isChecked(),
                "back_transform": self.back_transform.currentText(),
            }
        except Exception as exc:
            QMessageBox.critical(self, "Invalid settings", str(exc))
            return

        self.generate_btn.setEnabled(False)
        self.progress = QProgressDialog("Creating your print PDF...", None, 0, 0, self)
        self.progress.setWindowTitle("Working")
        self.progress.setCancelButton(None)
        self.progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.progress.show()

        self.worker_thread = QThread(self)
        self.worker = GenerateWorker(kwargs)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_generate_success)
        self.worker.failed.connect(self._on_generate_failed)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._on_thread_finished)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _on_generate_success(self, result) -> None:
        self._cleanup_busy_state()
        self.log.clear()
        self.log.append(f"Print PDF created: {result.output_path}")
        self.log.append(
            f"Layout: {result.rows} rows x {result.cols} columns ({result.cards_per_side} per page)"
        )
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Success")
        msg.setText("Your print PDF is ready.")
        open_btn = msg.addButton("Open File", QMessageBox.ButtonRole.AcceptRole)
        open_folder_btn = msg.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() is open_btn and result.output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(result.output_path.resolve())))
        elif msg.clickedButton() is open_folder_btn:
            folder = result.output_path.resolve().parent
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _on_generate_failed(self, error: str) -> None:
        self._cleanup_busy_state()
        self.log.append(f"Problem: {error}")
        QMessageBox.critical(self, "Generation failed", error)

    def _on_thread_finished(self) -> None:
        # Fallback cleanup if signals were interrupted.
        self._cleanup_busy_state()
        self.worker = None
        self.worker_thread = None

    def _cleanup_busy_state(self) -> None:
        self.generate_btn.setEnabled(True)
        if self.progress is not None:
            self.progress.close()
            self.progress = None


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Card Imposer")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
