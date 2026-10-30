from __future__ import annotations

import argparse
import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import black
from reportlab.pdfgen import canvas


OverlayPage: TypeAlias = PageObject

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0

PAGE_SIZES_PT = {
    "A3": (841.8897637795277, 1190.5511811023623),
    "A4": (595.2755905511812, 841.8897637795277),
    "A5": (419.52755905511816, 595.2755905511812),
    "LETTER": (612.0, 792.0),
    "LEGAL": (612.0, 1008.0),
}

BACK_TRANSFORMS = {
    "none",
    "rotate180",
    "mirrorX",
    "mirrorY",
    "mirrorX_rotate180",
    "mirrorY_rotate180",
}


@dataclass(frozen=True)
class GridSpec:
    rows: int
    cols: int
    positions: list[tuple[float, float]]
    card_width_pt: float
    card_height_pt: float
    page_width_pt: float
    page_height_pt: float
    margin_pt: float
    gap_pt: float


@dataclass(frozen=True)
class ImpositionResult:
    output_path: Path
    rows: int
    cols: int
    cards_per_side: int
    page_width_pt: float
    page_height_pt: float
    scale_percent: float
    back_transform: str


def mm_to_pt(mm: float) -> float:
    return (mm / MM_PER_INCH) * PT_PER_INCH


def load_pdf_pages(path: Path) -> tuple[PdfReader, PageObject, PageObject]:
    if not path.exists():
        raise FileNotFoundError(f"Input PDF not found: {path}")
    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    if page_count != 2:
        raise ValueError(
            f"Input PDF must contain exactly 2 pages (front/back). Found {page_count} pages."
        )
    return reader, reader.pages[0], reader.pages[1]


def _max_fit_count(total_space_pt: float, item_pt: float, gap_pt: float, axis_name: str) -> int:
    if item_pt <= 0:
        raise ValueError(f"Card {axis_name} must be > 0 pt. Got {item_pt}.")
    count = int((total_space_pt + gap_pt) // (item_pt + gap_pt))
    return max(count, 0)


def compute_grid(
    card_w_pt: float,
    card_h_pt: float,
    page_w_pt: float,
    page_h_pt: float,
    margin_pt: float,
    gap_pt: float,
    rows: int | None = None,
    cols: int | None = None,
) -> GridSpec:
    if margin_pt <= 0:
        raise ValueError(f"--margin-mm must be > 0. Got {margin_pt:.3f} pt.")
    if gap_pt <= 0:
        raise ValueError(f"--gap-mm must be > 0. Got {gap_pt:.3f} pt.")
    if rows is not None and rows <= 0:
        raise ValueError(f"--rows must be > 0. Got {rows}.")
    if cols is not None and cols <= 0:
        raise ValueError(f"--cols must be > 0. Got {cols}.")

    usable_w = page_w_pt - (2 * margin_pt)
    usable_h = page_h_pt - (2 * margin_pt)
    if usable_w <= 0 or usable_h <= 0:
        raise ValueError(
            f"Margins consume entire page. usable_w={usable_w:.3f}, usable_h={usable_h:.3f}."
        )

    max_cols = _max_fit_count(usable_w, card_w_pt, gap_pt, "width")
    max_rows = _max_fit_count(usable_h, card_h_pt, gap_pt, "height")

    if rows is None and cols is None:
        rows = max_rows
        cols = max_cols
    elif rows is None:
        rows = max_rows
    elif cols is None:
        cols = max_cols

    if rows is None or cols is None:
        raise RuntimeError("Internal error: rows/cols unresolved.")
    if rows <= 0 or cols <= 0:
        raise ValueError("Card cannot fit on page at current size with current margin/gap settings.")

    required_w = cols * card_w_pt + (cols - 1) * gap_pt
    required_h = rows * card_h_pt + (rows - 1) * gap_pt
    if required_w > usable_w + 1e-6 or required_h > usable_h + 1e-6:
        raise ValueError(
            "Requested rows/cols do not fit. "
            f"Required {required_w:.3f}x{required_h:.3f} pt, "
            f"available {usable_w:.3f}x{usable_h:.3f} pt."
        )

    start_x = margin_pt + (usable_w - required_w) / 2.0
    start_y = margin_pt + (usable_h - required_h) / 2.0

    positions: list[tuple[float, float]] = []
    for row in range(rows):
        for col in range(cols):
            x = start_x + col * (card_w_pt + gap_pt)
            y = start_y + row * (card_h_pt + gap_pt)
            positions.append((x, y))

    return GridSpec(
        rows=rows,
        cols=cols,
        positions=positions,
        card_width_pt=card_w_pt,
        card_height_pt=card_h_pt,
        page_width_pt=page_w_pt,
        page_height_pt=page_h_pt,
        margin_pt=margin_pt,
        gap_pt=gap_pt,
    )


def place_card(
    target_page: PageObject,
    source_page: PageObject,
    x: float,
    y: float,
    w: float,
    h: float,
    transform_mode: str,
    scale_factor: float = 1.0,
) -> None:
    if transform_mode not in BACK_TRANSFORMS:
        raise ValueError(f"Unknown transform mode: {transform_mode}")
    if scale_factor <= 0:
        raise ValueError(f"scale_factor must be > 0. Got {scale_factor}.")

    source_w = float(source_page.mediabox.width)
    source_h = float(source_page.mediabox.height)
    cx = source_w / 2.0
    cy = source_h / 2.0
    tx = x + (w / 2.0)
    ty = y + (h / 2.0)

    t = Transformation().translate(-cx, -cy).scale(scale_factor, scale_factor)
    if transform_mode == "rotate180":
        t = t.rotate(180)
    elif transform_mode == "mirrorX":
        t = t.scale(-1, 1)
    elif transform_mode == "mirrorY":
        t = t.scale(1, -1)
    elif transform_mode == "mirrorX_rotate180":
        t = t.scale(-1, 1).rotate(180)
    elif transform_mode == "mirrorY_rotate180":
        t = t.scale(1, -1).rotate(180)
    t = t.translate(tx, ty)
    target_page.merge_transformed_page(source_page, t, over=True, expand=False)


def _overlay_from_canvas_bytes(data: bytes) -> OverlayPage:
    reader = PdfReader(io.BytesIO(data))
    return reader.pages[0]


def _clip(val: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, val))


def _draw_clipped_line(
    c: canvas.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    nx1 = _clip(x1, x_min, x_max)
    ny1 = _clip(y1, y_min, y_max)
    nx2 = _clip(x2, x_min, x_max)
    ny2 = _clip(y2, y_min, y_max)
    if abs(nx1 - nx2) < 1e-6 and abs(ny1 - ny2) < 1e-6:
        return
    c.line(nx1, ny1, nx2, ny2)


def draw_crop_marks(
    page_w_pt: float,
    page_h_pt: float,
    positions: list[tuple[float, float]],
    card_w_pt: float,
    card_h_pt: float,
    margin_pt: float,
    gap_pt: float,
    label: str | None = None,
) -> OverlayPage:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_w_pt, page_h_pt))
    c.setStrokeColor(black)
    c.setFillColor(black)
    c.setLineWidth(0.5)

    mark_len = min(mm_to_pt(2.0), max(0.5, gap_pt / 2.0))
    x_min = margin_pt
    x_max = page_w_pt - margin_pt
    y_min = margin_pt
    y_max = page_h_pt - margin_pt

    for x, y in positions:
        x0 = x
        y0 = y
        x1 = x + card_w_pt
        y1 = y + card_h_pt

        _draw_clipped_line(c, x0 - mark_len, y0, x0, y0, x_min, x_max, y_min, y_max)
        _draw_clipped_line(c, x0, y0 - mark_len, x0, y0, x_min, x_max, y_min, y_max)
        _draw_clipped_line(c, x1, y0, x1 + mark_len, y0, x_min, x_max, y_min, y_max)
        _draw_clipped_line(c, x1, y0 - mark_len, x1, y0, x_min, x_max, y_min, y_max)
        _draw_clipped_line(c, x0 - mark_len, y1, x0, y1, x_min, x_max, y_min, y_max)
        _draw_clipped_line(c, x0, y1, x0, y1 + mark_len, x_min, x_max, y_min, y_max)
        _draw_clipped_line(c, x1, y1, x1 + mark_len, y1, x_min, x_max, y_min, y_max)
        _draw_clipped_line(c, x1, y1, x1, y1 + mark_len, x_min, x_max, y_min, y_max)
        if label:
            c.setFont("Helvetica", 6)
            c.drawString(x0 + mm_to_pt(1.0), y0 + mm_to_pt(1.0), label)

    c.showPage()
    c.save()
    return _overlay_from_canvas_bytes(buffer.getvalue())


def _resolve_page_size_pt(
    page_size: str, page_width_mm: float | None, page_height_mm: float | None
) -> tuple[float, float]:
    if page_width_mm is not None or page_height_mm is not None:
        if page_width_mm is None or page_height_mm is None:
            raise ValueError("Both --page-width-mm and --page-height-mm are required when setting custom size.")
        if page_width_mm <= 0 or page_height_mm <= 0:
            raise ValueError("Custom page width/height must be > 0.")
        return mm_to_pt(page_width_mm), mm_to_pt(page_height_mm)
    if page_size == "CUSTOM":
        raise ValueError("For --page-size CUSTOM, provide --page-width-mm and --page-height-mm.")
    return PAGE_SIZES_PT[page_size]


def impose_cards(
    input_path: Path,
    output_path: Path,
    page_size: str = "A4",
    page_width_mm: float | None = None,
    page_height_mm: float | None = None,
    margin_mm: float = 5.0,
    gap_mm: float = 3.0,
    rows: int | None = None,
    cols: int | None = None,
    scale_percent: float = 100.0,
    crop_marks: bool = False,
    test_sheet: bool = False,
    back_transform: str = "none",
) -> ImpositionResult:
    if scale_percent <= 0:
        raise ValueError(f"--scale-percent must be > 0. Got {scale_percent}.")

    page_w_pt, page_h_pt = _resolve_page_size_pt(page_size, page_width_mm, page_height_mm)
    margin_pt = mm_to_pt(margin_mm)
    gap_pt = mm_to_pt(gap_mm)
    scale_factor = scale_percent / 100.0

    _reader, front_page, back_page = load_pdf_pages(input_path)
    card_w_pt = float(front_page.mediabox.width) * scale_factor
    card_h_pt = float(front_page.mediabox.height) * scale_factor

    grid = compute_grid(
        card_w_pt=card_w_pt,
        card_h_pt=card_h_pt,
        page_w_pt=page_w_pt,
        page_h_pt=page_h_pt,
        margin_pt=margin_pt,
        gap_pt=gap_pt,
        rows=rows,
        cols=cols,
    )

    writer = PdfWriter()
    front_out = PageObject.create_blank_page(width=page_w_pt, height=page_h_pt)
    back_out = PageObject.create_blank_page(width=page_w_pt, height=page_h_pt)

    for x, y in grid.positions:
        place_card(
            target_page=front_out,
            source_page=front_page,
            x=x,
            y=y,
            w=grid.card_width_pt,
            h=grid.card_height_pt,
            transform_mode="none",
            scale_factor=scale_factor,
        )
        place_card(
            target_page=back_out,
            source_page=back_page,
            x=x,
            y=y,
            w=grid.card_width_pt,
            h=grid.card_height_pt,
            transform_mode=back_transform,
            scale_factor=scale_factor,
        )

    if crop_marks or test_sheet:
        front_overlay = draw_crop_marks(
            page_w_pt=page_w_pt,
            page_h_pt=page_h_pt,
            positions=grid.positions,
            card_w_pt=grid.card_width_pt,
            card_h_pt=grid.card_height_pt,
            margin_pt=grid.margin_pt,
            gap_pt=grid.gap_pt,
            label="F" if test_sheet else None,
        )
        back_overlay = draw_crop_marks(
            page_w_pt=page_w_pt,
            page_h_pt=page_h_pt,
            positions=grid.positions,
            card_w_pt=grid.card_width_pt,
            card_h_pt=grid.card_height_pt,
            margin_pt=grid.margin_pt,
            gap_pt=grid.gap_pt,
            label="B" if test_sheet else None,
        )
        front_out.merge_page(front_overlay)
        back_out.merge_page(back_overlay)

    writer.add_page(front_out)
    writer.add_page(back_out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        writer.write(f)

    return ImpositionResult(
        output_path=output_path,
        rows=grid.rows,
        cols=grid.cols,
        cards_per_side=len(grid.positions),
        page_width_pt=page_w_pt,
        page_height_pt=page_h_pt,
        scale_percent=scale_percent,
        back_transform=back_transform,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Impose a 2-page business-card PDF (front/back) on a print sheet."
    )
    parser.add_argument("input_pdf", help="Path to 2-page source PDF (page1=front, page2=back).")
    parser.add_argument("--output", help="Output PDF path (default: <input>_imposed.pdf).")
    parser.add_argument("--page-size", choices=[*PAGE_SIZES_PT.keys(), "CUSTOM"], default="A4")
    parser.add_argument("--page-width-mm", type=float, default=None)
    parser.add_argument("--page-height-mm", type=float, default=None)
    parser.add_argument("--margin-mm", type=float, default=5.0)
    parser.add_argument("--gap-mm", type=float, default=3.0)
    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--cols", type=int, default=None)
    parser.add_argument("--scale-percent", type=float, default=100.0)
    parser.add_argument("--crop-marks", choices=["on", "off"], default="off")
    parser.add_argument("--test-sheet", choices=["on", "off"], default="off")
    parser.add_argument("--back-transform", choices=sorted(BACK_TRANSFORMS), default="none")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    input_path = Path(args.input_pdf)
    if not input_path.exists():
        raise FileNotFoundError(f"Input PDF does not exist: {input_path}")

    if args.output:
        output_path = Path(args.output)
    else:
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path(__file__).resolve().parent
        output_path = base_dir / "outputs" / f"{input_path.stem}_imposed.pdf"

    result = impose_cards(
        input_path=input_path,
        output_path=output_path,
        page_size=args.page_size,
        page_width_mm=args.page_width_mm,
        page_height_mm=args.page_height_mm,
        margin_mm=args.margin_mm,
        gap_mm=args.gap_mm,
        rows=args.rows,
        cols=args.cols,
        scale_percent=args.scale_percent,
        crop_marks=args.crop_marks == "on",
        test_sheet=args.test_sheet == "on",
        back_transform=args.back_transform,
    )

    print(f"Imposed PDF created: {result.output_path}")
    print(
        f"Grid: {result.rows} rows x {result.cols} cols "
        f"({result.cards_per_side} cards per side)"
    )
    print(f"Back transform: {result.back_transform}")
    print(f"Scale percent: {result.scale_percent:.2f}%")
    print(
        f"Page size: {result.page_width_pt:.2f} x {result.page_height_pt:.2f} pt"
    )
    print("Print at Actual size (100%) and disable Fit to page.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
