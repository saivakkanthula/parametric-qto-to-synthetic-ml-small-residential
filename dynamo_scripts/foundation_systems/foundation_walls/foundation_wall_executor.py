# Dynamo CPython3
# Foundation Walls + Strip Footings + Cut Walls - Executor

import clr
import re

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import (
    WallType, WallFoundationType, WallFoundation,
    FilteredElementCollector, BuiltInParameter
)

clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

clr.AddReference("RevitNodes")
import Revit
clr.ImportExtensions(Revit.Elements)

clr.AddReference("ProtoGeometry")
from Autodesk.DesignScript.Geometry import Point, Line

doc = DocumentManager.Instance.CurrentDBDocument

# ----- Helpers ----------------------------------------------------

def safe_float(v, d=0.0):
    #Safely cast to float, return default if it fails
    try:
        return float(v)
    except:
        return d

def safe_bool(v, d=False):
    #Safely cast to bool, return default if it fails
    try:
        return bool(v)
    except:
        return d

def sort_keys(d):
    #Sort segment keys by trailing number (segment_1, segment_2, ...)
    def f(k):
        m = re.search(r"(\d+)$", str(k))
        return int(m.group(1)) if m else 10**9
    return sorted(list(d.keys()), key=f)

def sign_mult(s):
    #Convert "+" or "-" direction string to 1.0 or -1.0
    return 1.0 if str(s).strip() == "+" else -1.0

def elev_key(e):
    #Round elevation to 6 decimal places for use as cache key
    return round(float(e), 6)

def offset_point(pt, axis, sign, thk_ft):
    #Offset a 2D outer-face point inward to the wall centerline
    #For y-axis walls: offset in X. For x-axis walls: offset in Y
    x, y = pt
    h = thk_ft / 2.0
    s = sign_mult(sign)

    if axis == "y":
        return (x + s * h, y)
    elif axis == "x":
        return (x, y - s * h)
    else:
        raise Exception("Invalid axis: {}".format(axis))

#------ TYPE LOOKUP -------------------------------------------
#Revit family names must match exactly:
#  Foundation wall : wall_fndn_<material>_<thickness_in>in
#  Cut wall        : cut_wall_<material>_<thickness_in>_in
#  Strip footing   : wall_strip_footing_<width_in>_x_<thickness_in>_in


def get_wall_type(thk_ft, mat):
    thk = int(round(thk_ft * 12.0))
    name = "wall_fndn_{}_{}in".format(mat, thk)
    for wt in FilteredElementCollector(doc).OfClass(WallType).ToElements():
        p = wt.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        nm = p.AsString() if p else None
        if nm == name:
            return wt.ToDSType(True)
    return None

def get_cut_type(thk_ft, mat):
    thk = int(round(thk_ft * 12.0))
    name = "cut_wall_{}_{}_in".format(mat, thk)
    for wt in FilteredElementCollector(doc).OfClass(WallType).ToElements():
        p = wt.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        nm = p.AsString() if p else None
        if nm == name:
            return wt.ToDSType(True)
    return None

def get_footing_type(w_ft, t_ft):
    w = int(round(w_ft * 12.0))
    t = int(round(t_ft * 12.0))
    name = "wall_strip_footing_{}_x_{}_in".format(w, t)
    for ft in FilteredElementCollector(doc).OfClass(WallFoundationType).ToElements():
        p = ft.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        nm = p.AsString() if p else None
        if nm == name:
            return ft
    return None

#------ LEVEL CACHE -------------------------------------------
#Levels are created on demand and cached by elevation to avoid duplicates

def get_or_create_level(level0, cache, elev, prefix):
    k = elev_key(elev)
    if k in cache:
        return cache[k]

    name = "{}_{:.3f}ft".format(prefix, elev)
    lvl = Revit.Elements.Level.ByLevelOffsetAndName(level0, float(elev), name)
    cache[k] = lvl
    return lvl

#------ FLOOR THICKNESS LOOKUP --------------------------------
#Returns total floor thickness (joist depth + sheathing) in feet
#Used to compute cut wall top elevation
#ftype   : "type1" to "type16"
#fsheath : "lumber" or other (plywood / OSB)


def get_floor_thickness(ftype, fsheath):
    ftype = str(ftype).strip().lower()
    fsheath = str(fsheath).strip().lower()

    if fsheath == "lumber":
        if ftype in ["type1", "type2"]: return round((5.50 + 0.75) / 12.0, 3)
        elif ftype in ["type3", "type4"]: return round((5.50 + 0.688) / 12.0, 3)
        elif ftype in ["type5", "type6"]: return round((7.50 + 0.75) / 12.0, 3)
        elif ftype in ["type7", "type8"]: return round((7.50 + 0.688) / 12.0, 3)
        elif ftype in ["type9", "type10"]: return round((9.50 + 0.75) / 12.0, 3)
        elif ftype in ["type11", "type12"]: return round((9.50 + 0.688) / 12.0, 3)
        elif ftype in ["type13", "type14"]: return round((11.50 + 0.75) / 12.0, 3)
        elif ftype in ["type15", "type16"]: return round((11.50 + 0.688) / 12.0, 3)
    else:
        if ftype in ["type3", "type4"]: return round((5.50 + 0.5) / 12.0, 3)
        elif ftype == "type2": return round((5.50 + 0.625) / 12.0, 3)
        elif ftype == "type1": return round((5.50 + 0.75) / 12.0, 3)
        elif ftype in ["type7", "type8"]: return round((7.50 + 0.5) / 12.0, 3)
        elif ftype == "type6": return round((7.50 + 0.625) / 12.0, 3)
        elif ftype == "type5": return round((7.50 + 0.75) / 12.0, 3)
        elif ftype in ["type11", "type12"]: return round((9.50 + 0.5) / 12.0, 3)
        elif ftype == "type10": return round((9.50 + 0.625) / 12.0, 3)
        elif ftype == "type9": return round((9.50 + 0.75) / 12.0, 3)
        elif ftype in ["type15", "type16"]: return round((11.50 + 0.5) / 12.0, 3)
        elif ftype == "type14": return round((11.50 + 0.625) / 12.0, 3)
        elif ftype == "type13": return round((11.50 + 0.75) / 12.0, 3)

    raise Exception("Unsupported floor type / sheathing combination")

#------ INPUTS ------------------------------------------------
level_0         = IN[0]                     # Revit Level object — project datum (Level 0)
x_scale         = safe_float(IN[1], 1.0)    # Scale along building length
y_scale         = safe_float(IN[2], 1.0)    # Scale along building width
floor_type      = IN[3]                     # String - "type1" to "type16"
floor_sheathing = IN[4]                     # String - "lumber" or other
start_point_dict = IN[5]["start_point"]     # Dictionary
segments_dict   = IN[6]                     # Dictionary
mudsill_t       = safe_float(IN[7], 0.0)    # mudsill thickness in feet

floor_thk          = get_floor_thickness(floor_type, floor_sheathing)

floor_plus_mudsill = floor_thk + mudsill_t  # used for cut wall top elevation


#------ START POINT -------------------------------------------

base_x = safe_float(start_point_dict["x_fixed_ft"]) + safe_float(start_point_dict["x_variable_ft"]) * x_scale
base_y = safe_float(start_point_dict["y_fixed_ft"]) + safe_float(start_point_dict["y_variable_ft"]) * y_scale

#------ PREPROCESS --------------------------------------------
#Convert all segment values to working units (feet) and collect into data list

data = []
for k in sort_keys(segments_dict):
    s = segments_dict[k]

    axis = s["axis"]
    direction = s["direction"]

    #Segment length: fixed offset + variable part scaled by axis scale
    length_ft = safe_float(s["length_fixed_ft"]) + safe_float(s["length_variable_ft"]) * (x_scale if axis == "x" else y_scale)

    wall_thk_ft = safe_float(s["wall_thickness_in"]) / 12.0

    #Cut wall thickness = foundation wall thickness - joist bearing width
    cut_thk_ft = (safe_float(s["wall_thickness_in"]) - safe_float(s["joist_bearing_in"])) / 12.0

    data.append({
        "key": k,
        "axis": axis,
        "direction": direction,
        "length_ft": length_ft,

        "top_elevation_ft": safe_float(s["top_elevation_ft"]),
        "height_ft": safe_float(s["height_ft"]),

        "wall_thk_ft": wall_thk_ft,
        "wall_material": s["wall_material"],
        "has_wall": safe_bool(s["has_wall"]),

        "has_footing": safe_bool(s["has_footing"]),
        "footing_width_ft": safe_float(s["footing_width_in"]) / 12.0,
        "footing_thickness_ft": safe_float(s["footing_thickness_in"]) / 12.0,

        "has_cut_wall": safe_bool(s["has_cut_wall"]),
        "cut_wall_material": s["cut_wall_material"],
        "cut_thk_ft": cut_thk_ft
    })

#------ PASS 1: OUTER-FACE WALK -------------------------------
#Walk the outer face of the perimeter segment by segment
#Records raw outer_start and outer_end for each segment before any offset

x = base_x
y = base_y

for d in data:
    d["outer_start"] = (x, y)

    if d["axis"] == "x":
        x = x + sign_mult(d["direction"]) * d["length_ft"]
    else:
        y = y + sign_mult(d["direction"]) * d["length_ft"]

    d["outer_end"] = (x, y)


#------ PASS 2: CENTERLINE OFFSET -----------------------------
#Each segment is offset independently from outer face to centerline
#Different thicknesses between consecutive segments automatically produce a flush outer face with split centerline endpoints

for d in data:
    d["main_start"] = offset_point(d["outer_start"], d["axis"], d["direction"], d["wall_thk_ft"])
    d["main_end"]   = offset_point(d["outer_end"],   d["axis"], d["direction"], d["wall_thk_ft"])

    if d["has_cut_wall"] and d["cut_thk_ft"] > 0:
        d["cut_start"] = offset_point(d["outer_start"], d["axis"], d["direction"], d["cut_thk_ft"])
        d["cut_end"]   = offset_point(d["outer_end"],   d["axis"], d["direction"], d["cut_thk_ft"])


#------ PASS 3: ADJACENCY CORRECTION -------------------------
#At every axis-switching corner (x->y or y->x), snap the shared
#endpoint to a single joint coordinate to eliminate gaps/overlaps
#Applied to main walls always; cut walls only if both segments have them

for i in range(1, len(data)):
    prev = data[i - 1]
    curr = data[i]

    if prev["axis"] != curr["axis"]:
        # ---- MAIN WALLS: always correct, even if has_wall is False
        px1, py1 = prev["main_start"]
        px2, py2 = prev["main_end"]
        cx1, cy1 = curr["main_start"]
        cx2, cy2 = curr["main_end"]

        if prev["axis"] == "y" and curr["axis"] == "x":
            joint = (px2, cy1)
        elif prev["axis"] == "x" and curr["axis"] == "y":
            joint = (cx1, py2)
        else:
            raise Exception("Unexpected axis combination")

        prev["main_end"] = joint
        curr["main_start"] = joint

        # ---- CUT WALLS: only if both consecutive segments have cut walls
        if prev["has_cut_wall"] and curr["has_cut_wall"] and prev["cut_thk_ft"] > 0 and curr["cut_thk_ft"] > 0:
            cpx1, cpy1 = prev["cut_start"]
            cpx2, cpy2 = prev["cut_end"]
            ccx1, ccy1 = curr["cut_start"]
            ccx2, ccy2 = curr["cut_end"]

            if prev["axis"] == "y" and curr["axis"] == "x":
                cut_joint = (cpx2, ccy1)
            elif prev["axis"] == "x" and curr["axis"] == "y":
                cut_joint = (ccx1, cpy2)
            else:
                raise Exception("Unexpected cut axis combination")

            prev["cut_end"] = cut_joint
            curr["cut_start"] = cut_joint

# ------------------------------------------------------------
#------ CREATE ELEMENTS ---------------------------------------
#Each segment creates up to three Revit elements:
#  1. Foundation wall (if has_wall)
#  2. Strip footing attached to foundation wall (if has_footing)
#  3. Cut wall above foundation top for joist bearing pocket (if has_cut_wall)
#Failed segments are caught individually so one error does not abort the full run

level_cache = {elev_key(level_0.Elevation): level_0}
walls = []
footings = []
cut_walls = []
failed_items = []
debug_curves = []

for d in data:
    try:
        start_elev = d["top_elevation_ft"] - d["height_ft"]
        top_elev = d["top_elevation_ft"]

        start_level = get_or_create_level(level_0, level_cache, start_elev, "FW_START")
        top_level = get_or_create_level(level_0, level_cache, top_elev, "FW_TOP")

        # ---- MAIN WALL CURVE DEBUG
        mx1, my1 = d["main_start"]
        mx2, my2 = d["main_end"]

        debug_entry = {
            "segment": d["key"],
            "raw_outer_face_curve": {
                "start": d["outer_start"],
                "end": d["outer_end"]
            },
            "main_curve_xy": {
                "start": d["main_start"],
                "end": d["main_end"]
            },
            "main_curve_xyz": {
                "start": (mx1, my1, start_elev),
                "end": (mx2, my2, start_elev)
            }
        }

        #---- FOUNDATION WALL
        if d["has_wall"]:
            if abs(mx1 - mx2) < 1e-9 and abs(my1 - my2) < 1e-9:
                raise Exception("Zero-length main wall curve")

            wall_type = get_wall_type(d["wall_thk_ft"], d["wall_material"])
            if wall_type is None:
                raise Exception("Main wall type not found")

            p1 = Point.ByCoordinates(mx1, my1, start_elev)
            p2 = Point.ByCoordinates(mx2, my2, start_elev)
            curve = Line.ByStartPointEndPoint(p1, p2)

            wall = Revit.Elements.Wall.ByCurveAndLevels(curve, start_level, top_level, wall_type)
            walls.append(wall)

            #---- STRIP FOOTING
            if d["has_footing"]:
                footing_type = get_footing_type(d["footing_width_ft"], d["footing_thickness_ft"])
                if footing_type is None:
                    raise Exception("Footing type not found")

                db_wall = wall.InternalElement
                TransactionManager.Instance.EnsureInTransaction(doc)
                footing = WallFoundation.Create(doc, footing_type.Id, db_wall.Id)
                TransactionManager.Instance.TransactionTaskDone()
                footings.append(footing.ToDSType(True))

        # ---- CUT WALL CURVE DEBUG + CREATE
        if d["has_cut_wall"] and d["cut_thk_ft"] > 0:
            cx1, cy1 = d["cut_start"]
            cx2, cy2 = d["cut_end"]

            cut_top_elev = top_elev + floor_plus_mudsill
            cut_top_level = get_or_create_level(level_0, level_cache, cut_top_elev, "CUT_TOP")

            debug_entry["cut_curve_xy"] = {
                "start": d["cut_start"],
                "end": d["cut_end"]
            }
            debug_entry["cut_curve_xyz"] = {
                "start": (cx1, cy1, top_elev),
                "end": (cx2, cy2, top_elev)
            }

            if abs(cx1 - cx2) < 1e-9 and abs(cy1 - cy2) < 1e-9:
                raise Exception("Zero-length cut wall curve")

            cut_type = get_cut_type(d["cut_thk_ft"], d["cut_wall_material"])
            if cut_type is None:
                raise Exception("Cut wall type not found")

            cp1 = Point.ByCoordinates(cx1, cy1, top_elev)
            cp2 = Point.ByCoordinates(cx2, cy2, top_elev)
            ccurve = Line.ByStartPointEndPoint(cp1, cp2)

            cut_wall = Revit.Elements.Wall.ByCurveAndLevels(ccurve, top_level, cut_top_level, cut_type)
            cut_walls.append(cut_wall)

        debug_curves.append(debug_entry)

    except Exception as e:
        failed_items.append({
            "segment": d["key"],
            "error": str(e)
        })

OUT = walls, footings, cut_walls, failed_items, debug_curves