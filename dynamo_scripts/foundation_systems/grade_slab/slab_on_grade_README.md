# Slab-on-Grade — Segment Dictionary (`slab_on_grade_segment_dictionary.py`)

## Purpose

Defines the input dictionary consumed by the executor script.
Each entry describes one slab-on-grade floor: its Revit level, thickness,
start point, outline segments, and optional openings.

---

## Dynamo Inputs

| Port  | Variable  | Type    | Description                                                     |
|-------|-----------|---------|-----------------------------------------------------------------|
| IN[0] | `x_scale` | `float` | Scales all variable lengths of Segments parallel to X-axis      |
| IN[1] | `y_scale` | `float` | Scales all variable lengths of Segments parallel to Y-axis      |

`x_scale` and `y_scale` represent the parametric dimensions of the building
footprint. These indicate the percentage by which the rectangle enclosing the 
building footptint is scaled up or down. 

Fixed dimensions are unaffected by these values.

---

## Dictionary Schema

```
slab_on_grade_floors = {

    "floor_1": {

        "level"        : <Revit Level object>   # Level the slab is placed on
        "thickness_ft" : <float>                # Slab thickness in feet
        "has_openings" : <bool>                 # True if opening sub-dicts are present

        "start_point": {
            "x_fixed_ft"    : <float>           # Fixed X component of start point (ft)
            "x_variable_ft" : <float>           # X component scaled by x_scale (ft)
            "y_fixed_ft"    : <float>           # Fixed Y component of start point (ft)
            "y_variable_ft" : <float>           # Y component scaled by y_scale (ft)
        }

        "segments": {
            "segment_1": {
                "axis"               : "x" or "y"   # Movement axis
                "direction"          : "+" or "-"   # Movement direction
                "length_fixed_ft"    : <float>      # Fixed component of segment length (ft)
                "length_variable_ft" : <float>      # Variable component, scaled by axis scale (ft)
                "x_offset_ft"        : <float>      # X correction at this segment's start point (ft)
                "y_offset_ft"        : <float>      # Y correction at this segment's start point (ft)
                "forms_outline"      : <bool>       # True to include in final slab boundary
            }
            # ...
        }

        "opening_1": {                              # Only needed when has_openings = True
            "segment_1": {
                "axis"               : "x" or "y"
                "direction"          : "+" or "-"
                "length_fixed_ft"    : <float>
                "length_variable_ft" : <float>
                "x_offset_ft"        : <float>
                "y_offset_ft"        : <float>
                "forms_outline"      : <bool>
            }
            # ...
        }

        # "opening_2": { ... }
    }

    # "floor_2": { ... }
}
```

---

## Geometry Principles

### Start Point

The absolute origin of the segment chain is computed as:

```
X = x_fixed_ft + x_variable_ft * x_scale
Y = y_fixed_ft + y_variable_ft * y_scale
```

### Segment Length

Each segment moves along one axis by:

```
length = length_fixed_ft + length_variable_ft * axis_scale
```

where `axis_scale` is `x_scale` for X-axis segments and `y_scale` for Y-axis segments.

### Offset Logic

Offsets are applied independently to the **start point** of each segment
(i.e. to the raw corner produced by the Manhattan walk, not to the previous
segment's corrected end). A segment's offset therefore shifts:

- where the **current** segment starts, and
- where the **previous** segment ends.
- **In other words to preserve the 90° corner between two adjacent segments, the offset component along their shared axis must be equal.
  A Y-axis segment and the following X-axis segment must share the same x_offset_ft; an X-axis segment and the following Y-axis segment must share the same y_offset_ft.
  Violating this constraint will produce a slanted segment.**

This allows slab edges to be inset from foundation walls without modifying
segment lengths.

### `forms_outline` Flag

Only segments with `forms_outline = True` contribute to the final closed
boundary. Segments with `forms_outline = False` still participate in the
raw Manhattan walk (their lengths affect subsequent corner positions) but
are excluded from the Revit profile.

**This allows a single segment chain to describe multiple discontinuous slab regions — for example, two separate grade slabs or an interior slab and an exterior walkway that do not share an edge. Segments with `forms_outline = False` act as positional steps that advance the walk across the gap, keeping all geometry within one coordinate reference without forcing a shared boundary.**

### Openings

Each opening uses the **same start point** as its parent floor. Opening
segments follow identical rules to main outline segments. The executor
detects opening sub-dicts by their `opening_` key prefix.

---

## Notes

- All dimensions are in feet unless otherwise stated.
- All offsets must carry the correct sign.
- Segment keys must end in an integer suffix (`segment_1`, `segment_2`, …);
  they are processed in ascending numerical order.
- Opening keys must follow the same convention (`opening_1`, `opening_2`, …).
- The caller is responsible for the geometric correctness of the input.
