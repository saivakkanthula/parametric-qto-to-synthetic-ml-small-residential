# Slab-on-Grade — Executor (`slab_on_grade_execute.py`)

## Purpose

Consumes the dictionary produced by `slab_on_grade.py` and creates
slab-on-grade floors and openings in the active Revit document via Dynamo.

---

## Dynamo Inputs

| Port  | Variable       | Type    | Description                                      |
|-------|----------------|---------|--------------------------------------------------|
| IN[0] | `x_scale`      | `float` | Scales all variable X lengths                    |
| IN[1] | `y_scale`      | `float` | Scales all variable Y lengths                    |
| IN[2] | `floors_input` | `dict`  | The `slab_on_grade_floors` dict from the definition script |

`IN[2]` accepts either a **single floor dict** (the value of one `"floor_N"` entry)
or the full **dict-of-floors** (`slab_on_grade_floors`). Both formats are handled
automatically.

---

## Dynamo Outputs

| Port  | Variable        | Type           | Description                                              |
|-------|-----------------|----------------|----------------------------------------------------------|
| OUT[0]| `floors_out`    | `list`         | Created Dynamo Floor elements, one per floor             |
| OUT[1]| `openings_out`  | `list[list]`   | Created opening elements, nested per floor               |
| OUT[2]| `failed_items`  | `list[dict]`   | Error records for any floor or opening that failed       |
| OUT[3]| `debug`         | `list[dict]`   | Geometry and parameter trace for each processed floor    |

---

## Revit Requirements

### FloorType Naming Convention

The executor looks up a `FloorType` by name using the slab thickness.
The expected naming pattern is:

```
floor_concrete_slab_on_grade_<N>in
```

where `<N>` is the thickness in whole inches (rounded). For example:

| `thickness_ft` | Expected FloorType name                      |
|----------------|----------------------------------------------|
| `0.333`        | `floor_concrete_slab_on_grade_4in`           |
| `0.500`        | `floor_concrete_slab_on_grade_6in`           |
| `0.667`        | `floor_concrete_slab_on_grade_8in`           |

The FloorType must exist in the active Revit document before running the script.
If not found, the floor fails and an error is recorded in `failed_items`.

### Height Offset

After creation, each slab is pushed up by its own thickness using the
`Height Offset From Level` parameter, so the slab bottom face sits at the level elevation.

---

## Error Handling

Failures are isolated per floor — a single bad floor does not stop the others
from being created. Each entry in `failed_items` contains:

```python
{
    "floor_key" : "floor_1",        # which floor failed
    "stage"     : "floor_loop",     # where in execution it failed
    "error"     : "<message>"       # exception message
}
```

A top-level failure (e.g. `IN[2]` is `None`) is recorded with `"stage": "main"`.

---

## Debug Output

Each entry in `debug` (OUT[3]) contains a full geometry trace for one floor:

```python
{
    "floor_key"                : "floor_1",
    "base_start_xy"            : (x, y),        # computed start point
    "floor_type_name"          : "floor_concrete_slab_on_grade_8in",
    "thickness_ft"             : 0.667,
    "has_openings"             : False,
    "opening_count"            : 0,
    "raw_corners"              : [...],          # Manhattan walk corners before offsets
    "corrected_segment_starts" : [...],          # corners after per-segment offsets
    "outline_points_xy"        : [...],          # final boundary points used for Revit
    "main_segment_data"        : [               # per-segment breakdown
        {
            "segment"          : "segment_1",
            "axis"             : "x",
            "direction"        : "+",
            "scaled_length_ft" : 27.333,
            "x_offset_ft"      : 0.667,
            "y_offset_ft"      : 0.0,
            "forms_outline"    : True,
            "raw_start_xy"     : (x, y),
            "raw_end_xy"       : (x, y),
            "start_xy"         : (x, y),
            "end_xy"           : (x, y)
        }
        # ...
    ],
    "openings": [
        {
            "opening_key"              : "opening_1",
            "raw_corners"              : [...],
            "corrected_segment_starts" : [...],
            "outline_points_xy"        : [...]
        }
    ]
}
```

`raw_corners` and `corrected_segment_starts` are the primary tools for
diagnosing geometry mismatches.

---

## Notes

- Segment and opening keys must end in an integer suffix and are processed
  in ascending numerical order.
- All dimensions are in feet internally; conversion to Revit internal units
  is handled by the Dynamo geometry pipeline.
- The script requires an active Revit document and a valid Dynamo transaction context.
