# Task: Build an IFC to IGES/STEP Converter (CLI Tool)

## Overview
Create a Python command-line tool that converts IFC (Industry Foundation Classes) files to either IGES or STEP format using IfcOpenShell and Open CASCADE (via pythonocc-core).

## Requirements

### Environment Setup
- Python version - what is available on this machine
- Dependencies: `ifcopenshell`, `pythonocc-core` (install via conda: `conda install -c conda-forge pythonocc-core ifcopenshell`)

### CLI Interface
The tool must be a single-file script `ifc_converter.py` that:
1. Accepts an IFC file path as input (user pastes or types the path)
2. Prompts the user to choose output format: `1` for STEP, `2` for IGES
3. Saves the output file in the same directory as the input file, with the same base name but `.step` or `.iges` extension
4. Prints progress: which IFC entities are being processed, how many total, and a final success/failure summary

### Example session:

$ python ifc_converter.py

=== IFC to IGES/STEP Converter ===

Enter path to IFC file: /home/user/models/building.ifc

Choose output format:
  [1] STEP (.step)
  [2] IGES (.iges)

Your choice: 1

Processing: /home/user/models/building.ifc
Found 342 geometric entities.
Converting [1/342] IfcWall #123 ... OK
Converting [2/342] IfcSlab #456 ... OK
...
Converting [342/342] IfcWindow #789 ... OK

Done! 340/342 entities converted successfully (2 skipped).
Output saved to: /home/user/models/building.step

### Core Logic
1. **Parse IFC**: Use `ifcopenshell.open()` to load the file. Extract all `IfcProduct` entities that have geometric representations.
2. **Convert geometry**: Use `ifcopenshell.geom.create_shape()` with appropriate settings to get Open CASCADE `TopoDS_Shape` objects. Settings should enable `USE_PYTHON_OPENCASCADE = True` (so shapes are native pythonocc objects) and `WELD_VERTICES = True`.
3. **Export STEP**: Use `OCC.Core.STEPControl.STEPControl_Writer` with `STEPControl_AsIs` mode. Set the schema to AP214.
4. **Export IGES**: Use `OCC.Core.IGESControl.IGESControl_Writer`. Call `ComputeModel()` before `Write()`.
5. **Error handling**: Validate the input file exists and has `.ifc` extension. Wrap each entity conversion in try/except — log failures but continue processing remaining entities. If zero entities convert successfully, exit with error code 1. Handle keyboard interrupt (Ctrl+C) gracefully.

### Code Quality
- Add a docstring at the top explaining usage
- Use `pathlib.Path` for all file path handling
- Keep it in a single file, no unnecessary abstractions
- Add type hints to all functions
- Use `if __name__ == "__main__":` entry point

### Edge Cases to Handle
- IFC file with no geometric entities → print warning and exit
- Entities with no valid geometry (e.g. `IfcSpace` or openings) → skip with warning
- Very large files → print a warning if entity count exceeds 5000
- Output file already exists → ask user to confirm overwrite
- Invalid file path or permission errors → clear error message