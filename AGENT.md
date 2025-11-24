This project is python program for an interactive gantt chart builder using PyQt6.

There are 6 menu options available to a user:
- New
- Open
- Save
- Save As
- Export
- Change Duration

New creates a new Gantt chart (see below), Open loads an existing gantt chart from the file system, Save writes back to the current file, and Save As prompts for a new filename before persisting the current project.

New/Open/Save/Save As all expose the native keyboard shortcuts for the current OS (e.g., Cmd+N/Cmd+O/Cmd+S/Cmd+Shift+S on macOS, Ctrl+N/Ctrl+O/Ctrl+S/Ctrl+Shift+S on Windows/Linux) via Qt's standard key sequences, so users can stay in their normal workflow without reaching for the mouse.

When new is selected the user is prompted (via a dialogue) as to how long the project will run. This is an integer. The user is then shown a blank project.

The project itself can be best thought of as a table with 4 areas namely a textual "task name", integer "start" and "end" values and a visualisation area. The task-name column now supports manual resizing directly from its header so users can widen it for lengthy labels or shrink it to create more space for the schedule grid; the summary row mirrors the same width to keep the layout aligned. Individual rows also remember arbitrary schedule segments so the textual info, start/end columns, and visual intervals all stay in sync.

Rows can be reordered directly in the UI: drag any populated row by its task cell (or row header) and drop it where the insertion guide appears. The blank append row is ignored during this process, undo snapshots are captured before the move, and the summary row automatically mirrors the new ordering.

The grid happily stores "work in progress" rows. Users can type only a task name (or just a tentative start/end) and still save, reopen, export, or change the project duration without losing that partially filled data. Visual timelines, summary counts, and exported CSV/PDF files only light up periods when both start and end values are present, but the textual columns are always preserved.

The visualisation area is itself a table with columns ranging from 1 to the project duration.

The user can add new entries to the table (by either adding something at the bottom of a blank row) or right-clicking on an existing row and selecting "Insert row" which inserts a blank row *after* the current row. When right-clicking within the visualization columns the context menu also exposes a "Split at period N" action whenever the clicked day falls inside the task's active interval, instantly creating multiple segments without leaving the grid.

The user can fill in a task name and the start and end dates and a bar appears in the visualisation area covering the relevant period.

Tasks can be edited directly on the grid: drag the edges of any interval (or the entire bar) to lengthen, shorten, or reposition that segment while keeping the textual columns consistent. These interactions respect multi-interval tasks by only adjusting the dragged segment and automatically merging overlapping pieces.

At the very bottom of the visualisation area is a summary. For each column it displays the number of tasks which exist at that point in time.

Finally, the user can select a row as a "Work package" (again via right-clicking). These work packages are logical groups of tasks and should be highlighted appropriately when exported. The context menu displays the usual checkmark beside "Toggle work package" whenever the selected row is currently flagged, so it is always obvious whether the row is active. The user can also de-select a row as a workpackage if it was selected as one previously.

# Command-line loading

Running `python -m gantt_maker <project.csv>` (or passing a path into `run(path=...)`) instructs the application to load that CSV immediately after the main window appears. If the first CLI argument is omitted or the file does not exist, the app simply falls back to spawning a fresh project and notifies the user when auto-open fails.

# Open and Save

Projects should be saved as CSV files containing minimal relevant data to allow them to be loaded (via Open). Save As mirrors Save but always prompts for a new path first, so users can branch variants without overwriting the original plan.

# Export

Exporting a project should allow the user to save the content of the Gantt chart either as a CSV or a PDF.

Exported CSV files should contain Task/Start/End columns followed by a column for every period, where active periods are marked (e.g. "X" for normal tasks, "W" for work packages). PDF exports should render the entire task grid (excluding the summary row) on a landscape page with no blank margin beyond the final column, highlighting work packages as in the UI, and may optionally hide the Start/End columns based on user preference.

Storage and export both serialize the new interval data: CSV persistence now includes an `intervals` column (existing legacy files without it continue to load), and exporters derive their day-by-day markers from the stored segments so multi-interval tasks render identically everywhere.





