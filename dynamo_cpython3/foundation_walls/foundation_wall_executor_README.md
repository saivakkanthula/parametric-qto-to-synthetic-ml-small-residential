# Foundation Walls — Executor

## What does the Executor do?

The executor reads the start point and segments dictionary and creates three types of Revit elements along the foundation perimeter — foundation walls, strip footings, and cut walls. Failed segments are caught individually so one error does not abort the full run.

---

## Inputs

| IN | Type | Description |
|---|---|---|
| IN[0] | Revit Level | Project datum — Level 0 |
| IN[1] | float | x_scale — scale multiplier along building length |
| IN[2] | float | y_scale — scale multiplier along building width |
| IN[3] | string | Floor type — "type1" to "type16" |
| IN[4] | string | Floor sheathing — "lumber" or other (plywood/OSB) |
| IN[5] | dict | start_point_dict — output of foundation_start_point.py |
| IN[6] | dict | segments_dict — output of foundation_segments_<id>.py |
| IN[7] | float | Mudsill thickness in feet |

## Outputs

| OUT | Type | Description |
|---|---|---|
| OUT[0] | list | Foundation wall elements |
| OUT[1] | list | Strip footing elements |
| OUT[2] | list | Cut wall elements |
| OUT[3] | list | Failed segments — each entry is `{"segment": key, "error": message}` |
| OUT[4] | list | Debug curves — outer face, centerline XY and XYZ per segment |

---

## Algorithm

**Preprocess** — reads every segment, converts units (inches to feet), computes final lengths using x_scale and y_scale, and collects everything into a working list.

**Pass 1 — Outer-face walk** — starts at the start point and walks segment by segment along the outer face of the foundation, recording raw start and end points for each segment before any offset.

**Pass 2 — Centerline offset** — each segment is offset independently from the outer face to the wall centerline by half its wall thickness. Because this is done independently per segment, thickness changes between consecutive segments automatically produce a flush outer face with split centerline endpoints.

**Pass 3 — Adjacency correction** — at every axis-switching corner (x→y or y→x), the shared endpoint is snapped to a single joint coordinate to eliminate gaps and overlaps. Applied to foundation walls always; cut walls only if both segments have them.

**Create elements** — walks the processed data and creates up to three Revit elements per segment: foundation wall, strip footing attached to that wall, and cut wall above the foundation top.

---

## Revit Family Naming Conventions

Type lookup will return None and the segment will fail if family names do not match exactly.

| Element | Pattern | Example |
|---|---|---|
| Foundation wall | `wall_fndn_<material>_<thickness_in>in` | `wall_fndn_concrete_block_10in` |
| Cut wall | `cut_wall_<material>_<thickness_in>_in` | `cut_wall_concrete_8_in` |
| Strip footing | `wall_strip_footing_<width_in>_x_<thickness_in>_in` | `wall_strip_footing_20_x_8_in` |

---

## Floor Type Lookup

Used to compute cut wall top elevation: `cut wall top = foundation top + floor thickness + mudsill thickness`

| Type | Joist Size | Spacing | Sheathing (lumber) | Sheathing (plywood/OSB) |
|---|---|---|---|---|
| type1 | 2×6 | 24 in | 3/4 in | 3/4 in |
| type2 | 2×6 | 20 in | 3/4 in | 5/8 in |
| type3 | 2×6 | 16 in | 11/16 in | 1/2 in |
| type4 | 2×6 | 12 in | 11/16 in | 1/2 in |
| type5 | 2×8 | 24 in | 3/4 in | 3/4 in |
| type6 | 2×8 | 20 in | 3/4 in | 5/8 in |
| type7 | 2×8 | 16 in | 11/16 in | 1/2 in |
| type8 | 2×8 | 12 in | 11/16 in | 1/2 in |
| type9 | 2×10 | 24 in | 3/4 in | 3/4 in |
| type10 | 2×10 | 20 in | 3/4 in | 5/8 in |
| type11 | 2×10 | 16 in | 11/16 in | 1/2 in |
| type12 | 2×10 | 12 in | 11/16 in | 1/2 in |
| type13 | 2×12 | 24 in | 3/4 in | 3/4 in |
| type14 | 2×12 | 20 in | 3/4 in | 5/8 in |
| type15 | 2×12 | 16 in | 11/16 in | 1/2 in |
| type16 | 2×12 | 12 in | 11/16 in | 1/2 in |