# Dynamo CPython3
# ------------------------------------------------------------
# SLAB-ON-GRADE / WALKWAY SLAB + OPTIONAL OPENINGS
#
# INPUTS
#   IN[0] : x_scale       (float)
#   IN[1] : y_scale       (float)
#   IN[2] : floors_dict   (dict)  -- see slab_on_grade.py for schema
#
# OUTPUT
#   OUT = (floors_out, openings_out, failed_items, debug)
# ------------------------------------------------------------

import re
import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")
clr.AddReference("RevitNodes")
clr.AddReference("ProtoGeometry")

import Autodesk.Revit.DB as DB
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

import Revit
clr.ImportExtensions(Revit.GeometryConversion)
clr.ImportExtensions(Revit.Elements)

from Autodesk.DesignScript.Geometry import Point, Line, PolyCurve

doc = DocumentManager.Instance.CurrentDBDocument

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

NEAR_ZERO = 1e-9    # tolerance for point coincidence checks
MIN_LENGTH = 1e-12  # minimum valid segment length (ft)


# ------------------------------------------------------------
# General utilities
# ------------------------------------------------------------

def safe_float(value, default=0.0):
    """Cast *value* to float, returning *default* on any failure."""
    try:
        if value in (None, "None", "none", ""):
            return default
        return float(value)
    except Exception:
        return default


def safe_bool(value, default=False):
    """Cast *value* to bool, returning *default* on any failure."""
    try:
        return bool(value)
    except Exception:
        return default


def dict_get(d, key, default=None):
    """Get *key* from *d*, supporting both Python dicts and IronPython mappings."""
    try:
        return d.get(key, default)
    except Exception:
        pass
    try:
        if d.ContainsKey(key):
            return d[key]
    except Exception:
        pass
    try:
        return d[key]
    except Exception:
        return default


def sort_numeric_keys(dct):
    """Return dict keys sorted by their trailing integer suffix."""
    try:
        keys = list(dct.keys())
    except Exception:
        try:
            keys = list(dct.Keys)
        except Exception:
            keys = []

    def _trailing_int(k):
        match = re.search(r"(\d+)$", str(k))
        return int(match.group(1)) if match else 10 ** 9

    return sorted(keys, key=_trailing_int)


# ------------------------------------------------------------
# Geometry utilities
# ------------------------------------------------------------

def sign_from_direction(direction):
    """Return +1.0 or -1.0 from a direction string (``"+"`` / ``"-"``)."""
    s = str(direction).strip().lower()
    if s in ("+", "+ve", "positive", "pos", "1"):
        return 1.0
    if s in ("-", "-ve", "negative", "neg", "-1"):
        return -1.0
    raise ValueError("Invalid direction '{}'".format(direction))


def axis_scale(axis, x_scale, y_scale):
    """Return the scale factor that corresponds to *axis* (``"x"`` or ``"y"``)."""
    a = str(axis).strip().lower()
    if a == "x":
        return float(x_scale)
    if a == "y":
        return float(y_scale)
    raise ValueError("Invalid axis '{}'".format(axis))


def points_coincident(p, q, tol=NEAR_ZERO):
    """Return True when two DS Points are within *tol* of each other."""
    return abs(p.X - q.X) <= tol and abs(p.Y - q.Y) <= tol and abs(p.Z - q.Z) <= tol


# ------------------------------------------------------------
# Revit utilities
# ------------------------------------------------------------

def unwrap(elem):
    """Return the underlying Revit DB element from a Dynamo wrapper."""
    return elem.InternalElement if hasattr(elem, "InternalElement") else elem


def get_floor_type(thickness_ft):
    """Find the FloorType whose name matches the slab thickness convention.

    Naming convention: ``floor_concrete_slab_on_grade_<N>in``
    where *N* is the thickness rounded to the nearest inch.

    Returns
    -------
    tuple[DB.FloorType, str]
        The matched FloorType and its name string.

    Raises
    ------
    Exception
        When no matching FloorType is found in the document.
    """
    inches = int(round(float(thickness_ft) * 12.0))
    target = "floor_concrete_slab_on_grade_{}in".format(inches)

    for ft in DB.FilteredElementCollector(doc).OfClass(DB.FloorType).ToElements():
        param = ft.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
        if param and param.AsString() == target:
            return ft, target

    raise Exception("FloorType '{}' not found in document.".format(target))


def create_floor(polycurve, floor_type, level):
    """Create a Revit floor from a DS PolyCurve, FloorType, and Level."""
    wrapped_type = (
        floor_type.ToDSType(True)
        if not hasattr(floor_type, "InternalElement")
        else floor_type
    )
    return Revit.Elements.Floor.ByOutlineTypeAndLevel(polycurve, wrapped_type, level)


def set_height_offset(floor_elem, offset_ft):
    """Set the 'Height Offset From Level' parameter on *floor_elem*."""
    try:
        return floor_elem.SetParameterByName("Height Offset From Level", float(offset_ft))
    except Exception:
        return floor_elem


def to_db_curve(ds_or_db_curve):
    """Convert a DS or DB curve to a list of ``DB.Curve`` objects."""
    if isinstance(ds_or_db_curve, DB.Curve):
        return [ds_or_db_curve]
    try:
        converted = ds_or_db_curve.ToRevitType(True)
        if isinstance(converted, DB.Curve):
            return [converted]
        try:
            return list(converted)
        except TypeError:
            return [converted]
    except Exception as e:
        raise TypeError("Cannot convert curve to DB.Curve: {}".format(e))


def make_curve_array(curves):
    """Build a ``DB.CurveArray`` from a list of DS or DB curves."""
    ca = DB.CurveArray()
    items = curves if isinstance(curves, (list, tuple)) else [curves]
    for c in items:
        for db_c in to_db_curve(c):
            ca.Append(db_c)
    return ca


def create_opening(host_elem, boundary_curves):
    """Cut a perpendicular opening in *host_elem* using *boundary_curves*.

    Parameters
    ----------
    host_elem:
        A Dynamo-wrapped or raw DB Floor / Ceiling / RoofBase / Toposolid.
    boundary_curves:
        List of DS or DB curves forming the closed opening boundary.

    Raises
    ------
    TypeError
        When *host_elem* is not a supported Revit host type.
    """
    host = unwrap(host_elem)
    if not isinstance(host, (DB.Floor, DB.Ceiling, DB.RoofBase, DB.Toposolid)):
        raise TypeError("Host must be Floor, Ceiling, Roof, or Toposolid.")

    curve_array = make_curve_array(boundary_curves)

    TransactionManager.Instance.EnsureInTransaction(doc)
    try:
        opening = doc.Create.NewOpening(host, curve_array, True)
    finally:
        TransactionManager.Instance.TransactionTaskDone()

    return opening


# ------------------------------------------------------------
# Input parsing
# ------------------------------------------------------------

def parse_start_point(start_dict, x_scale, y_scale):
    """Compute the absolute (X, Y) start point from the scaled start-point dict.

    Returns
    -------
    tuple[float, float]
    """
    x = safe_float(dict_get(start_dict, "x_fixed_ft", 0.0)) \
      + safe_float(dict_get(start_dict, "x_variable_ft", 0.0)) * x_scale
    y = safe_float(dict_get(start_dict, "y_fixed_ft", 0.0)) \
      + safe_float(dict_get(start_dict, "y_variable_ft", 0.0)) * y_scale
    return x, y


def parse_segments(seg_dict, x_scale, y_scale):
    """Parse and validate all segments, computing scaled lengths.

    Returns
    -------
    list[dict]
        Ordered list of fully-resolved segment records.

    Raises
    ------
    Exception
        On missing segments, invalid axis/direction, or zero-length segments.
    """
    ordered_keys = sort_numeric_keys(seg_dict)
    if not ordered_keys:
        raise Exception("No segments found.")

    segments = []

    for key in ordered_keys:
        seg = dict_get(seg_dict, key)
        if seg is None:
            raise Exception("Segment '{}' not found.".format(key))

        seg_axis      = str(dict_get(seg, "axis", "")).strip().lower()
        seg_direction = str(dict_get(seg, "direction", "")).strip()
        length_fixed  = safe_float(dict_get(seg, "length_fixed_ft", 0.0))
        length_var    = safe_float(dict_get(seg, "length_variable_ft", 0.0))
        x_off         = safe_float(dict_get(seg, "x_offset_ft", 0.0))
        y_off         = safe_float(dict_get(seg, "y_offset_ft", 0.0))
        forms_outline = safe_bool(dict_get(seg, "forms_outline", True))

        if seg_axis not in ("x", "y"):
            raise Exception("Invalid axis '{}' in segment '{}'.".format(seg_axis, key))

        scale      = axis_scale(seg_axis, x_scale, y_scale)
        scaled_len = length_fixed + length_var * scale

        if scaled_len <= MIN_LENGTH:
            raise Exception("Segment '{}' has zero or negative length.".format(key))

        segments.append({
            "key":              key,
            "axis":             seg_axis,
            "direction":        seg_direction,
            "length_fixed_ft":  length_fixed,
            "length_variable_ft": length_var,
            "axis_scale":       scale,
            "scaled_length_ft": scaled_len,
            "x_offset_ft":      x_off,
            "y_offset_ft":      y_off,
            "forms_outline":    forms_outline,
        })

    return segments


# ------------------------------------------------------------
# Geometry builder
# ------------------------------------------------------------

def build_outline_points(base_x, base_y, base_z, seg_dict, x_scale, y_scale):
    """Build the ordered DS Points that define the slab or opening outline.

    Algorithm
    ---------
    1. Walk all segments from the base start to produce ``raw_corners``.
    2. Apply each segment's offset independently to its raw corner
       → ``corrected_starts``.
    3. Collect ``corrected_starts`` for segments where ``forms_outline=True``
       as the final outline point list.

    Returns
    -------
    tuple[list[Point], list[dict], list[tuple], list[tuple]]
        outline_points, enriched segment records, raw_corners, corrected_starts
    """
    segments = parse_segments(seg_dict, x_scale, y_scale)
    n = len(segments)

    # --- Step 1: raw Manhattan walk ---
    raw_corners = [(base_x, base_y)]
    rx, ry = base_x, base_y

    for seg in segments:
        s = sign_from_direction(seg["direction"])
        L = seg["scaled_length_ft"]
        if seg["axis"] == "x":
            rx += s * L
        else:
            ry += s * L
        raw_corners.append((rx, ry))

    # --- Step 2: per-corner offset corrections ---
    corrected_starts = [
        (raw_corners[i][0] + segments[i]["x_offset_ft"],
         raw_corners[i][1] + segments[i]["y_offset_ft"])
        for i in range(n)
    ]

    # --- Step 3: enrich segment records with geometry data ---
    for i, seg in enumerate(segments):
        end_xy = corrected_starts[(i + 1) % n]
        seg.update({
            "raw_start_xy":  raw_corners[i],
            "raw_end_xy":    raw_corners[i + 1],
            "start_xy":      corrected_starts[i],
            "end_xy":        end_xy,
            "start_point":   Point.ByCoordinates(corrected_starts[i][0], corrected_starts[i][1], base_z),
            "end_point":     Point.ByCoordinates(end_xy[0], end_xy[1], base_z),
        })

    # --- Step 4: collect outline points for forms_outline segments ---
    form_indices = [i for i, seg in enumerate(segments) if seg["forms_outline"]]
    if not form_indices:
        raise Exception("No segment has forms_outline=True.")

    outline_points = []
    for j, idx in enumerate(form_indices):
        next_idx = form_indices[(j + 1) % len(form_indices)]
        start_xy = corrected_starts[idx]
        end_xy   = corrected_starts[next_idx]

        segments[idx]["outline_start_xy"] = start_xy
        segments[idx]["outline_end_xy"]   = end_xy

        if j == 0:
            outline_points.append(Point.ByCoordinates(start_xy[0], start_xy[1], base_z))
        outline_points.append(Point.ByCoordinates(end_xy[0], end_xy[1], base_z))

    return outline_points, segments, raw_corners, corrected_starts


def build_closed_polycurve(points):
    """Convert an ordered list of DS Points into a closed PolyCurve.

    Duplicate consecutive points are removed before line construction.

    Returns
    -------
    tuple[PolyCurve, list[Line]]

    Raises
    ------
    Exception
        When fewer than 4 points remain, or fewer than 3 valid edges result.
    """
    if not points or len(points) < 4:
        raise Exception("Not enough points to build a closed outline.")

    # Remove consecutive duplicates
    cleaned = []
    for p in points:
        if not cleaned or not points_coincident(cleaned[-1], p):
            cleaned.append(p)

    # Close the loop
    if not points_coincident(cleaned[0], cleaned[-1]):
        cleaned.append(cleaned[0])

    lines = [
        Line.ByStartPointEndPoint(cleaned[i], cleaned[i + 1])
        for i in range(len(cleaned) - 1)
        if not points_coincident(cleaned[i], cleaned[i + 1])
    ]

    if len(lines) < 3:
        raise Exception("Outline has fewer than 3 valid edges.")

    return PolyCurve.ByJoinedCurves(lines), lines


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

x_scale      = safe_float(IN[0], 1.0)
y_scale      = safe_float(IN[1], 1.0)
floors_input = IN[2]

floors_out   = []
openings_out = []
failed_items = []
debug        = []

try:
    if floors_input is None:
        raise Exception("IN[2] (floors_dict) is None.")

    # Accept a single-floor dict or a dict-of-floors
    if dict_get(floors_input, "level") is not None:
        floors_dict = {"floor_1": floors_input}
    else:
        floors_dict = floors_input

    floor_keys = sort_numeric_keys(floors_dict)

    for floor_key in floor_keys:
        try:
            floor_data = dict_get(floors_dict, floor_key)
            if floor_data is None:
                raise Exception("Could not read floor data.")

            # --- Read floor properties ---
            level         = dict_get(floor_data, "level")
            thickness_ft  = dict_get(floor_data, "thickness_ft")
            has_openings  = safe_bool(dict_get(floor_data, "has_openings", False))
            start_dict    = dict_get(floor_data, "start_point")
            segments_dict = dict_get(floor_data, "segments")

            if level is None:
                raise Exception("'level' is None.")
            if thickness_ft is None:
                raise Exception("'thickness_ft' is None.")
            if start_dict is None:
                raise Exception("'start_point' is None.")
            if segments_dict is None:
                raise Exception("'segments' is None.")

            thickness_ft = safe_float(thickness_ft)
            base_z       = float(level.Elevation)

            floor_type, floor_type_name = get_floor_type(thickness_ft)
            base_x, base_y = parse_start_point(start_dict, x_scale, y_scale)

            # --- Build main slab outline ---
            main_points, main_segs, raw_corners, corrected_starts = build_outline_points(
                base_x, base_y, base_z, segments_dict, x_scale, y_scale
            )
            main_polycurve, main_curves = build_closed_polycurve(main_points)

            floor_elem = create_floor(main_polycurve, floor_type, level)
            floor_elem = set_height_offset(floor_elem, thickness_ft)

            # --- Build openings ---
            created_openings = []
            opening_debug    = []

            if has_openings:
                opening_keys = [
                    k for k in sort_numeric_keys(floor_data)
                    if str(k).strip().lower().startswith("opening_")
                ]

                for opening_key in opening_keys:
                    opening_seg_dict = dict_get(floor_data, opening_key)
                    if opening_seg_dict is None:
                        continue

                    op_points, op_segs, op_raw, op_corrected = build_outline_points(
                        base_x, base_y, base_z, opening_seg_dict, x_scale, y_scale
                    )
                    _, op_curves = build_closed_polycurve(op_points)

                    opening_elem = create_opening(floor_elem, op_curves)

                    created_openings.append(opening_elem)
                    opening_debug.append({
                        "opening_key":              opening_key,
                        "raw_corners":              op_raw,
                        "corrected_segment_starts": op_corrected,
                        "outline_points_xy":        [(p.X, p.Y) for p in op_points],
                    })

            floors_out.append(floor_elem)
            openings_out.append(created_openings)

            debug.append({
                "floor_key":                floor_key,
                "base_start_xy":            (base_x, base_y),
                "floor_type_name":          floor_type_name,
                "thickness_ft":             thickness_ft,
                "has_openings":             has_openings,
                "opening_count":            len(created_openings),
                "raw_corners":              raw_corners,
                "corrected_segment_starts": corrected_starts,
                "outline_points_xy":        [(p.X, p.Y) for p in main_points],
                "main_segment_data": [
                    {
                        "segment":          seg["key"],
                        "axis":             seg["axis"],
                        "direction":        seg["direction"],
                        "scaled_length_ft": seg["scaled_length_ft"],
                        "x_offset_ft":      seg["x_offset_ft"],
                        "y_offset_ft":      seg["y_offset_ft"],
                        "forms_outline":    seg["forms_outline"],
                        "raw_start_xy":     seg["raw_start_xy"],
                        "raw_end_xy":       seg["raw_end_xy"],
                        "start_xy":         seg["start_xy"],
                        "end_xy":           seg["end_xy"],
                    }
                    for seg in main_segs
                ],
                "openings": opening_debug,
            })

        except Exception as floor_err:
            failed_items.append({
                "floor_key": floor_key,
                "stage":     "floor_loop",
                "error":     str(floor_err),
            })

except Exception as main_err:
    failed_items.append({
        "stage": "main",
        "error": str(main_err),
    })

OUT = (floors_out, openings_out, failed_items, debug)
