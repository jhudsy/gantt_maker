This project is python program for an interactive gantt chart builder using PyQt6.

There are 5 menu options available to a user:
- New
- Open
- Save
- Export
- Change Duration

New creates a new Gantt chart (see below), while Open opens an existing gantt chart from the file system and save saves the current chart.

When new is selected the user is prompted (via a dialogue) as to how long the project will run. This is an integer. The user is then shown a blank project.

The project itself can be best thought of as a table with 4 areas namely a textual "task name", integer "start" and "end"  values and a visualisation area.

The visualisation area is itself a table with columns ranging from 1 to the project duration.

The user can add new entries to the table (by either adding something at the bottom of a blank row) or right-clicking on an existing row and selecting "Insert row" which inserts a blank row *after* the current row.

The user can fill in a task name and the start and end dates and a bar appears in the visualisation area covering the relevant period.

The user can also drag the edges of the bar in the visualisation area left and right to change the project duration. This should be reflected in the start date.

At the very bottom of the visualisation area is a summary. For each column it displays the number of tasks which exist at that point in time.

Finally, the user can select a row as a "Work package" (again via right-clicking). These work packages are logical groups of tasks and should be highlighted appropriately when exported. The user can also de-select a row as a workpackage if it was selected as one previously.

# Open and Save

Projects should be saved as CSV files containing minimal relevant data to allow them to be loaded (via Open).

# Export

Exporting a project should allow the user to save the content of the Gantt chart either as a CSV or a PDF.

Exported CSV files should contain Task/Start/End columns followed by a column for every period, where active periods are marked (e.g. "X" for normal tasks, "W" for work packages). PDF exports should render the entire task grid (excluding the summary row) on a landscape page with no blank margin beyond the final column, highlighting work packages as in the UI, and may optionally hide the Start/End columns based on user preference.





