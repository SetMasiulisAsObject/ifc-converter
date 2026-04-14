"""
IFC to STEP Converter
=====================
Usage:
    python ifc_converter.py

Prompts for an IFC file path, then converts all geometric entities to STEP
(.stp) using IfcConvert (part of the IfcOpenShell project).

Key IfcConvert flags used:
  --unify-shapes               merge touching/overlapping shapes
  --convert-back-units         output coordinates in mm (IFC native)
  --weld-vertices              merge near-duplicate vertices so OCC can close
                               IfcFacetedBrep shells into MANIFOLD_SOLID_BREP
  --reorient-shells            fix inconsistent face orientations so shells
                               pass the closed-solid check

Without --weld-vertices and --reorient-shells, IfcConvert writes every
IfcFacetedBrep face as a separate 1-face SHELL_BASED_SURFACE_MODEL (open
surface sheet), which SolidWorks cannot import as a solid body.

Dependencies:
    pip install ifcopenshell
    IfcConvert.exe — place next to this script or on PATH.
    Download from: https://github.com/IfcOpenShell/IfcOpenShell/releases
"""

import sys
import subprocess
import tempfile
import threading
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ifcopenshell


# ── IfcConvert discovery ──────────────────────────────────────────────────────

def find_ifcconvert() -> Path:
    import shutil
    candidates = [
        Path.home() / "AppData" / "Local" / "IfcConvert-standalone" / "IfcConvert.exe",
        Path(__file__).parent / "IfcConvert.exe",
        Path("C:/Program Files/IfcOpenShell/IfcConvert.exe"),
        Path("C:/Program Files (x86)/IfcOpenShell/IfcConvert.exe"),
        Path.home() / "IfcOpenShell" / "IfcConvert.exe",
    ]
    for p in candidates:
        if p.exists():
            return p
    found = shutil.which("IfcConvert") or shutil.which("IfcConvert.exe")
    if found:
        return Path(found)
    raise FileNotFoundError(
        "IfcConvert.exe not found.\n"
        "Place IfcConvert.exe next to this script, or download it from:\n"
        "  https://github.com/IfcOpenShell/IfcOpenShell/releases"
    )


# ── User prompts ──────────────────────────────────────────────────────────────

def get_ifc_path() -> Path:
    while True:
        raw = input("\nEnter path to IFC file: ").strip().strip('"').strip("'")
        path = Path(raw)
        if not path.exists():
            print(f"  Error: File not found: {path}")
            continue
        if path.suffix.lower() != ".ifc":
            print(f"  Error: Expected a .ifc file, got '{path.suffix}'")
            continue
        return path


def confirm_overwrite(path: Path) -> bool:
    answer = input(f"\n  '{path.name}' already exists. Overwrite? [y/N]: ").strip().lower()
    return answer == "y"


def count_geometric_products(ifc_model: ifcopenshell.file) -> int:
    return sum(1 for p in ifc_model.by_type("IfcProduct") if p.Representation is not None)


# ── Console output helpers ────────────────────────────────────────────────────

def _safe_print(text: str, end: str = "\n") -> None:
    try:
        print(text, end=end, flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), end=end, flush=True)


def _tail_log(log_path: Path, stop_event: threading.Event) -> tuple[int, int]:
    converted = skipped = 0
    last_progress = ""
    with open(log_path, encoding="utf-16-le", errors="replace") as f:
        while not stop_event.is_set():
            line = f.readline()
            if not line:
                time.sleep(0.05)
                continue
            line = line.rstrip("\r\n\x00")
            if not line.strip():
                continue
            lower = line.lower()
            if "\r" in line or "%" in line or "creating geometry" in lower:
                clean = line.replace("\r", "").strip()
                if clean and clean != last_progress:
                    _safe_print(f"\r  {clean:<70}", end="")
                    last_progress = clean
            elif "successfully" in lower or "written" in lower:
                converted += 1
                if last_progress:
                    _safe_print("")
                    last_progress = ""
                _safe_print(f"  {line}")
            elif "skipping" in lower or "skipped" in lower or "failed" in lower:
                skipped += 1
                if last_progress:
                    _safe_print("")
                    last_progress = ""
                _safe_print(f"  {line}")
            else:
                if last_progress:
                    _safe_print("")
                    last_progress = ""
                _safe_print(f"  {line}")
        for line in f:
            line = line.rstrip("\r\n\x00")
            if not line.strip():
                continue
            lower = line.lower()
            if "successfully" in lower or "written" in lower:
                converted += 1
            elif "skipping" in lower or "skipped" in lower or "failed" in lower:
                skipped += 1
            _safe_print(f"  {line}")
    if last_progress:
        _safe_print("")
    return converted, skipped


def run_conversion(
    ifcconvert: Path,
    ifc_path: Path,
    output_path: Path,
) -> tuple[bool, int, int]:
    """Run IfcConvert, streaming its log output in real time."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False, mode="wb") as tmp:
            log_path = Path(tmp.name)

        cmd = [
            str(ifcconvert),
            str(ifc_path),
            str(output_path),
            "--yes",
            "--log-format", "plain",
            "--unify-shapes",
            "--convert-back-units",
            "--weld-vertices",
            "--reorient-shells",
        ]

        with open(log_path, "wb") as out_file:
            proc = subprocess.Popen(cmd, stdout=out_file, stderr=subprocess.DEVNULL)

        stop_event = threading.Event()
        result: list = [0, 0]

        def tailer():
            c, s = _tail_log(log_path, stop_event)
            result[0], result[1] = c, s

        t = threading.Thread(target=tailer, daemon=True)
        t.start()
        proc.wait()
        stop_event.set()
        t.join(timeout=5)
        log_path.unlink(missing_ok=True)

        success = proc.returncode == 0 and output_path.exists()
        return success, result[0], result[1]
    except Exception as exc:
        print(f"  Error running IfcConvert: {exc}")
        return False, 0, 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n=== IFC to STEP Converter ===")

    try:
        try:
            ifcconvert = find_ifcconvert()
        except FileNotFoundError as exc:
            print(f"\nError: {exc}")
            sys.exit(1)

        ifc_path = get_ifc_path()

        output_path = ifc_path.with_suffix(".stp")
        if output_path.exists() and not confirm_overwrite(output_path):
            print("Aborted.")
            sys.exit(0)

        print(f"\nReading: {ifc_path}")
        try:
            ifc_model = ifcopenshell.open(str(ifc_path))
        except Exception as exc:
            print(f"Error: Could not open IFC file: {exc}")
            sys.exit(1)

        entity_count = count_geometric_products(ifc_model)
        if entity_count == 0:
            print("Warning: No geometric entities found. Nothing to convert.")
            sys.exit(0)

        print(f"Found {entity_count} geometric entities.")
        if entity_count > 5000:
            print(f"Warning: Large file ({entity_count} entities). This may take a while.")

        print(f"\nConverting to STEP via IfcConvert...\n")
        success, converted, skipped = run_conversion(ifcconvert, ifc_path, output_path)
        if not success:
            print("\nError: Conversion failed.")
            sys.exit(1)
        print(f"\nDone! Output saved to: {output_path}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
