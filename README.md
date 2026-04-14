# IFC to STEP Converter

Converts IFC (Industry Foundation Classes) files to STEP (`.stp`) format as proper solid bodies, ready for import into SolidWorks or other CAD tools.

## Why this tool

Standard IFC→STEP converters often write `IfcFacetedBrep` geometry (slabs, stairs, complex shapes) as individual open surface sheets (`SHELL_BASED_SURFACE_MODEL`) instead of closed solid bodies (`MANIFOLD_SOLID_BREP`). SolidWorks cannot form solids from these and reports _"Unable to create solid from trimmed surfaces"_.

This converter uses IfcConvert with `--weld-vertices` and `--reorient-shells` flags to ensure every element that can be a solid is written as one.

---

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.10+ | [python.org](https://www.python.org/downloads/) |
| ifcopenshell | `pip install ifcopenshell` |
| IfcConvert.exe | Free standalone binary — see below |

### Installing IfcConvert

Download the latest `IfcConvert-v*.exe` from the [IfcOpenShell releases page](https://github.com/IfcOpenShell/IfcOpenShell/releases) and place it in **one** of these locations (checked in order):

```
%LOCALAPPDATA%\IfcConvert-standalone\IfcConvert.exe   ← recommended
<folder containing ifc_converter.py>\IfcConvert.exe
C:\Program Files\IfcOpenShell\IfcConvert.exe
C:\Program Files (x86)\IfcOpenShell\IfcConvert.exe
anywhere on your system PATH
```

---

## Usage

### Option A — Run the Python script directly

```
python ifc_converter.py
```

The script prompts for the IFC file path, then writes a `.stp` file next to the original.

```
=== IFC to STEP Converter ===

Enter path to IFC file: C:\Projects\building.ifc

Reading: C:\Projects\building.ifc
Found 165 geometric entities.

Converting to STEP via IfcConvert...

  [1/165] IfcWall ... written successfully
  ...

Done! Output saved to: C:\Projects\building.stp
```

### Option B — Run the standalone EXE (no Python needed)

Build once:

```
pip install pyinstaller
pyinstaller --onefile --console --name "IFC-to-STEP" --collect-all ifcopenshell ifc_converter.py
```

The executable is created at `dist\IFC-to-STEP.exe`. Copy it anywhere — desktop, shared drive, etc. — and double-click to run. IfcConvert.exe still needs to be installed separately.

---

## Output

The `.stp` file is written to the same folder as the input IFC, with the same base name:

```
C:\Projects\building.ifc  →  C:\Projects\building.stp
```

If the output file already exists you will be asked to confirm overwrite.

---

## What gets converted

| IFC geometry type | STEP output |
|---|---|
| `IfcExtrudedAreaSolid` | `MANIFOLD_SOLID_BREP` (solid) |
| `IfcBooleanResult` / `IfcBooleanClippingResult` | `MANIFOLD_SOLID_BREP` (solid) |
| `IfcFacetedBrep` (walls, slabs, stairs, …) | `MANIFOLD_SOLID_BREP` (solid) |
| `IfcMappedItem` (instanced geometry) | expanded and converted as above |

Door and window openings are **not** subtracted from walls/slabs (`--disable-opening-subtractions`), so every element is a clean closed solid suitable for mass-property calculations.

---

## IfcConvert flags used

| Flag | Effect |
|---|---|
| `--unify-shapes` | Merge touching/overlapping shapes per element |
| `--convert-back-units` | Output coordinates in millimetres (IFC native) |
| `--disable-opening-subtractions` | Keep walls and slabs as closed solids |
| `--weld-vertices` | Merge near-duplicate vertices so shells close correctly |
| `--reorient-shells` | Fix inconsistent face normals before solid check |
