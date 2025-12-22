# Revit/Dynamo Anchor Modeling Architecture (Proposal)

This document reviews the current approach to creating anchor families from multi-view DWG inputs and proposes a revised architecture that fills key gaps for robustness and reuse.

## Observed Gaps
- **Input validation:** No guardrails around DWG import plane, scale, units, or required layers; missing normalization for origin-to-origin alignment.
- **Layer parsing:** Layer naming convention is defined but lacks schema validation and helpful diagnostics for typos or missing combinations (e.g., `EXT` without matching `PLN/SEC`).
- **Geometry reconciliation:** Width/depth fusion rules between plan/front/side are implicit; there is no conflict resolution or prioritization when profiles disagree.
- **Coordinate systems:** No abstraction for mapping DWG coordinates to Revit Family coordinates and handling Left/Right vs Front/Back orientation changes.
- **Parameterization:** Family parameters are not centralized; extrusion thickness/offsets are not exposed for downstream schedulable parameters (e.g., Width, Height, Thickness, StiffenerOffset).
- **Void sequencing:** Void cutting assumes “through-all” without control over cut order or optional cuts; no dependency graph between parts and voids.
- **Error reporting:** Dynamo/Python nodes lack structured logging and user-facing warnings; troubleshooting is difficult when layers are missing or self-intersecting.
- **Reusability:** Mixed responsibilities (DWG read, geometry fusion, extrusion, parameter push) inside a single script node; no testable pure-Python core.

## Revised Architecture
### 1) Data Contracts & Validation Layer
- **Schema:** Define a JSON/YAML schema describing valid layer tokens (`PARCA`, `ISLEM`, `KAYNAK`) and allowed combinations; validate incoming layer names and provide actionable messages in Dynamo UI.
- **Import metadata:** Capture DWG view name, scale, insertion point, and layer list before geometry processing; refuse to run if any required view or layer is missing.
- **Units & tolerances:** Normalize all coordinates to Revit internal units and enforce tolerances for coincident points/collinearity.

### 2) Layer Parsing & Geometry Extraction
- **Parser module:** Convert layer names into structured objects (`Part`, `Operation`, `Plane`). Map `PLN`, `FRT`, `SEC` to Revit sketch planes.
- **Profile builders:** For each part, build 2D profiles per plane. Support polylines, arcs, and bulge segments; heal small gaps within a tolerance.
- **Conflict detection:** When plan/front/side dimensions disagree, surface a warning and select precedence rules (e.g., `SEC` governs thickness, `PLN` governs width, `FRT` governs height).

### 3) Fusion & Centering Strategy
- **Dimension fusion:** Compute final `Width/Height/Thickness` from fused profiles; support centered and edge-aligned modes via a `Center_Mode` flag.
- **Offset handling:** Allow per-part offsets (e.g., stiffener inset) with defaults from settings. Persist computed offsets into shared parameters.
- **Symmetry helpers:** If only half-profiles are supplied, mirror around reference planes when `Center_Mode` is true.

### 4) Solid/Void Construction Pipeline
- **Operation graph:** Build solids first (`EXT`), then apply voids (`VOID`) in deterministic order; allow optional “selective cut” for voids targeting specific parts.
- **Through-all control:** Support `ThroughAll`, `Blind`, and `UpToNext` cut modes based on layer suffixes (e.g., `VOID_TA`, `VOID_BLIND_50`).
- **Join/boolean hygiene:** After each operation, run join/uncut rules to prevent unintended merges; detect self-intersection and fail fast.

### 5) Parameter & Family Output
- **Parameter map:** Centralize mapping from computed dimensions to Revit Family parameters (e.g., `Width`, `Height`, `Thickness`, `CutDepth`, `StiffenerWidth`). Allow toggling `Param_Mode` to skip writes during dry-runs.
- **Reference planes & constraints:** Create or reuse named reference planes per part to anchor extrusions; lock sketches to planes for future parametric edits.
- **Type/instance separation:** Decide which parameters are type-based (standard anchor sizes) versus instance-based (hole offsets); expose to schedules.

### 6) Diagnostics & UX
- **Structured logging:** Emit categorized messages (INFO/WARN/ERROR) to Dynamo watch nodes; include offending layer names and suggested fixes.
- **Preview mode:** Optional wireframe preview of fused profiles and extrusion extents before commit; highlight missing layers in color.
- **Run flags:** Keep `Run`, `Center_Mode`, and `Param_Mode` flags but add `Preview_Mode` and `Validate_Only` for safe iterations.

### 7) Packaging & Testing
- **Modular Python:** Split into modules (`layers.py`, `profiles.py`, `fusion.py`, `builder.py`, `params.py`, `logging.py`) so logic can be unit-tested outside Revit via geometry stubs.
- **Sample fixtures:** Include DWG fixtures and expected parameter outputs for regression tests; script a headless “dry-run” that reads DWG geometry and reports fused dimensions.
- **Versioning:** Embed a version stamp in the Dynamo graph and Python module to trace builds; document compatibility with Revit/Dynamo releases.

## Minimal Dynamo Wiring (per input)
- **IN[0]/IN[1]/IN[2]:** DWG `ImportInstance` elements for Plan, Front, Side views.
- **IN[3]:** Settings list `[Run, Center_Mode, Param_Mode, Preview_Mode, Validate_Only]`.
- **OUT:**
  - `Solids`: Built solid geometries per part
  - `Voids`: Applied void features
  - `Parameters`: Dict of written parameters and values
  - `Log`: List of structured messages

## Execution Flow
1. Collect DWG imports and validate schema/layers.
2. Parse layers → profiles per plane.
3. Fuse dimensions with centering/offset rules.
4. Build solids; apply voids with chosen cut mode.
5. Push parameters; join geometry; emit diagnostics.

This architecture keeps the current multi-view workflow while adding validation, clearer data contracts, and reusable modules that make anchor variants and stiffener-heavy parts easier to support.
