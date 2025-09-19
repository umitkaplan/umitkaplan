"""Convert Revit model lines into wall elements."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

try:  # Autodesk modules are only available inside Revit based hosts.
    import Autodesk.Revit.DB as DB
    import Autodesk.Revit.UI as UI
except ImportError:  # pragma: no cover - executed outside Revit.
    DB = None  # type: ignore[assignment]
    UI = None  # type: ignore[assignment]

DEFAULT_HEIGHT_MM = 3000.0
_MIN_CURVE_LENGTH = 1e-6


def _require_revit() -> None:
    if DB is None:
        raise RuntimeError("Revit API is not available. Run this script inside Revit.")


def _get_unit_type_id() -> object:
    _require_revit()

    try:  # Revit 2021+
        return DB.UnitTypeId.Millimeters
    except AttributeError:  # pragma: no cover - legacy API branch
        return DB.DisplayUnitType.DUT_MILLIMETERS


def _mm_to_internal(length_mm: float) -> float:
    _require_revit()
    return DB.UnitUtils.ConvertToInternalUnits(length_mm, _get_unit_type_id())


def _active_documents() -> Tuple[Optional[UI.UIDocument], Optional[DB.Document]]:
    uidoc = doc = None

    try:  # pyRevit and RevitPythonShell export __revit__
        uidoc = __revit__.ActiveUIDocument  # type: ignore[name-defined]
        doc = uidoc.Document if uidoc else None
    except NameError:
        pass

    if doc is None:
        try:  # Dynamo supplies a DocumentManager helper
            from RevitServices.Persistence import DocumentManager  # type: ignore

            manager = DocumentManager.Instance
            uidoc = manager.CurrentUIApplication.ActiveUIDocument
            doc = manager.CurrentDBDocument
        except Exception:
            pass

    return uidoc, doc


def _collect_model_curves(doc: DB.Document, uidoc: Optional[UI.UIDocument]) -> Sequence[DB.ModelCurve]:
    _require_revit()

    curves: List[DB.ModelCurve] = []

    if uidoc is not None:
        selection = list(uidoc.Selection.GetElementIds())
        if selection:
            for element_id in selection:
                element = doc.GetElement(element_id)
                if isinstance(element, DB.ModelCurve):
                    curves.append(element)

            if curves:
                return curves

    collector = DB.FilteredElementCollector(doc, doc.ActiveView.Id).OfClass(DB.ModelCurve)
    return [curve for curve in collector if isinstance(curve, DB.ModelCurve)]


def _default_level(doc: DB.Document) -> DB.Level:
    _require_revit()

    view = doc.ActiveView
    level = getattr(view, "GenLevel", None)
    if isinstance(level, DB.Level):
        return level

    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level))
    if not levels:
        raise RuntimeError("The document does not contain any levels.")

    return min(levels, key=lambda item: item.Elevation)


def _default_wall_type(doc: DB.Document) -> DB.WallType:
    _require_revit()

    type_id = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.WallType)
    if type_id and type_id != DB.ElementId.InvalidElementId:
        element = doc.GetElement(type_id)
        if isinstance(element, DB.WallType):
            return element

    wall_type = DB.FilteredElementCollector(doc).OfClass(DB.WallType).FirstElement()
    if wall_type is None:
        raise RuntimeError("The document does not contain any wall types.")

    return wall_type  # type: ignore[return-value]


def _create_walls(
    doc: DB.Document,
    curves: Iterable[DB.ModelCurve],
    wall_type: DB.WallType,
    base_level: DB.Level,
    height_mm: float,
    structural: bool,
) -> List[DB.ElementId]:
    _require_revit()

    created: List[DB.ElementId] = []
    height_internal = _mm_to_internal(height_mm)

    transaction = DB.Transaction(doc, "Create Walls From Model Lines")
    transaction.Start()

    try:
        for curve_element in curves:
            curve = curve_element.GeometryCurve
            if curve is None or curve.Length < _MIN_CURVE_LENGTH:
                continue

            try:
                wall = DB.Wall.Create(
                    doc,
                    curve,
                    wall_type.Id,
                    base_level.Id,
                    height_internal,
                    0.0,
                    False,
                    structural,
                )
            except Exception:
                wall = DB.Wall.Create(doc, curve, wall_type.Id, base_level.Id, structural)
                if wall is not None:
                    param = wall.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM)
                    if param and not param.IsReadOnly:
                        param.Set(height_internal)

            if wall is not None:
                created.append(wall.Id)

        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise

    return created


def _notify(title: str, message: str) -> None:
    if UI is None:
        print(f"{title}: {message}")
        return

    try:
        UI.TaskDialog.Show(title, message)
    except Exception:  # pragma: no cover - UI errors should not crash execution
        print(f"{title}: {message}")


def run(default_height_mm: float = DEFAULT_HEIGHT_MM, structural: bool = False) -> None:
    if DB is None:
        print("The Revit API is not available. Run this script inside Revit.")
        return

    uidoc, doc = _active_documents()
    if doc is None:
        raise RuntimeError("Unable to obtain the active Revit document.")

    model_curves = _collect_model_curves(doc, uidoc)
    if not model_curves:
        _notify("Model Lines To Walls", "No model lines were found in the active view or selection.")
        return

    wall_type = _default_wall_type(doc)
    base_level = _default_level(doc)

    created = _create_walls(doc, model_curves, wall_type, base_level, default_height_mm, structural)

    _notify(
        "Model Lines To Walls",
        "Created {0} walls using type '{1}' on level '{2}'.".format(
            len(created), wall_type.Name, base_level.Name
        ),
    )


if __name__ == "__main__":  # pragma: no cover - helpful for quick manual execution
    run()
