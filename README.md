# Card Imposer (CLI + PyQt GUI)

Reusable print-imposition tool for 2-page business-card PDFs:
- Page 1 = FRONT design
- Page 2 = BACK design

Output is a 2-page print-ready PDF (any supported size):
- Output page 1: imposed fronts
- Output page 2: imposed backs in identical positions for duplex cut alignment

## Install

```powershell
cd c:\Users\PlayerX\Desktop\m\card_imposer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Fast start (copy/paste)

From `c:\Users\PlayerX\Desktop\m\card_imposer`:

```powershell
python impose_cards_gui.py
```

Notes:
- GUI is PyQt-based (faster than Tkinter for this app).
- You must run `Preview Layout` before `Generate Imposed PDF`.
- Header includes `Instructions`, `Portfolio`, and `GitHub`.
- On `Generate`, a loading dialog is shown until the PDF is finished.

If you want CLI directly:

```powershell
python impose_cards.py "..\Blue White Illustrated Cleaning Service Business Card.pdf" --crop-marks on --test-sheet on
```

Scale cards to 120% before imposition:

```powershell
python impose_cards.py "..\Blue White Illustrated Cleaning Service Business Card.pdf" --scale-percent 120
```

## CLI Usage

```powershell
python impose_cards.py "c:\path\to\cards.pdf"
```

Default output:
- `cards_imposed.pdf` in the same folder as input.

### Auto-fit at 100% with crop marks

```powershell
python impose_cards.py "c:\path\to\cards.pdf" --crop-marks on
```

### Force 2 columns x 5 rows

```powershell
python impose_cards.py "c:\path\to\cards.pdf" --cols 2 --rows 5 --scale-percent 100
```

### Use a different print size

Preset:
```powershell
python impose_cards.py "c:\path\to\cards.pdf" --page-size LETTER
```

Custom mm:
```powershell
python impose_cards.py "c:\path\to\cards.pdf" --page-size CUSTOM --page-width-mm 300 --page-height-mm 450
```

### Try duplex transform options

```powershell
python impose_cards.py "c:\path\to\cards.pdf" --back-transform none
python impose_cards.py "c:\path\to\cards.pdf" --back-transform rotate180
python impose_cards.py "c:\path\to\cards.pdf" --back-transform mirrorX
python impose_cards.py "c:\path\to\cards.pdf" --back-transform mirrorY
python impose_cards.py "c:\path\to\cards.pdf" --back-transform mirrorX_rotate180
python impose_cards.py "c:\path\to\cards.pdf" --back-transform mirrorY_rotate180
```

### Test-sheet labels

```powershell
python impose_cards.py "c:\path\to\cards.pdf" --crop-marks on --test-sheet on
```

From GUI:
- Choose print size preset or `CUSTOM` width/height in mm.
- Use `Instructions` in the header for the built-in guide.
- Preview is schematic and updates to selected print size.

## Print instructions

- Print at `Actual size` / `100%`
- Disable `Fit to page`
- Start tests with duplex `Flip on short edge`
- If back orientation is wrong, try transform values in this order:
  1. `none`
  2. `rotate180`
  3. `mirrorX`
  4. `mirrorY`
  5. `mirrorX_rotate180`
  6. `mirrorY_rotate180`

## Notes

- Input PDF must contain exactly 2 pages or the tool raises an error.
- Scaling is supported with `--scale-percent` (100 means source size).
- Margins and gaps are in millimeters and converted to points for PDF placement precision.
