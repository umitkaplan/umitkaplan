# Model Lines to Walls Script

This repository contains `model_lines_to_walls.py`, a Revit Python script
that converts straight or curved model lines (`ModelCurve` elements) into
wall instances. The script is designed for Revit hosts such as pyRevit,
RevitPythonShell, or Dynamo's Python node.

## Usage

1. In Revit, draw the model lines that describe the wall layout. You may
   select a subset of lines before running the script; when nothing is
   selected the script falls back to every model line visible in the active
   view.
2. Run the script from your preferred Revit Python environment. Newly
   created walls will adopt the document default wall type and the level
   associated with the active view (or the lowest level in the file if the
   view lacks a level reference).
3. After the transaction completes a dialog (or a console printout when a
   UI dialog cannot be shown) reports how many walls were created.

> Note: Running `model_lines_to_walls.py` in a plain CPython interpreter will
> simply print a short explanation because the Autodesk Revit API is not
> available outside Revit.
