# Gantt Maker

Interactive desktop tool for drafting simple Gantt charts with PyQt6.

## Features
- Create, open, save, and export projects (CSV/PDF)
- Editable grid with task names, start/end periods, and a live bar visualization
- Drag bar edges to tweak task duration directly on the timeline
- Quick row insertion/deletion, work-package tagging, and undo for accidental deletes via the context menu
- Right-click timeline cells to apply colors from a standard palette or a custom picker
- Right-click any populated row to apply/clear color across all timeline cells in that row
- Right-click timeline cells to place/remove a colored diamond either in-cell or on the cell boundary
- Landscape PDF and CSV exports that include the entire timeline grid (Task/Start/End plus one column per period, filled for active spans)
- Live summary row showing concurrent task counts per period

## Requirements
- Python 3.10+
- PyQt6 (installed via `pyproject.toml` dependencies)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# or include dev tools (pytest)
pip install -e '.[dev]'
```

## Run the app
```bash
python -m gantt_maker
```

You can also pass a CSV path directly (e.g., `python -m gantt_maker my_project.csv`) and the file will open automatically on launch.

Use the File menu to create a new project (you will be prompted for the duration), open existing CSV files, save progress, or export to CSV/PDF. Right-click rows inside the table to insert new rows, toggle work-package highlighting, and set row colors. Right-click timeline cells to set or clear individual cell colors and to add/remove diamonds with palette or custom colors.

Row color applies only to the task's active periods, not to empty timeline cells. Clearing an individual cell color restores the active-period color if one exists, or white if it does not.

### Adjusting the duration
To change the project duration after tasks already exist, select **File → Change Duration...** and enter the new number of periods. Tasks will be clamped automatically if they exceed the new bounds.

### Exports
- **File → Export → PDF** produces a formatted landscape page with the entire task grid (without the summary row). You will be prompted whether to include the Start/End columns; work packages retain their highlight color.
- **File → Export → CSV** writes a rich matrix that mirrors the PDF (Task/Start/End columns followed by one column per period populated with `X` or `W`). This is distinct from **Save**, which stores the minimal CSV needed to reopen a project.

### Save format compatibility
- **Save** now stores interval data, cell colors, and diamond markers so UI styling reopens exactly as edited.
- Existing saved files from earlier versions still load (legacy headers are supported).

The main window now opens wide enough to show the default 20-period timeline, so horizontal scrolling is rarely necessary for small projects.

## Tests
```bash
pip install -e '.[dev]'
python -m pytest
```

The current automated coverage exercises the CSV persistence helpers. GUI-driven workflows can be verified manually by running the application.
