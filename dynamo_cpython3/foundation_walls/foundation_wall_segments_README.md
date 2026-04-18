# Foundation Walls — Segments Dictionary

## What is the Segments Dictionary?

The segments dictionary defines the foundation perimeter as an ordered sequence of straight wall runs, parallel to X-axis or Y-axis, called segments. The executor reads this dictionary and walks the segments in numeric order starting from the start point, creating foundation walls, strip footings, and cut walls in Revit.

## How it Connects

- **Start Point** → defines where segment_1 begins (outer-face origin)
- **Segments Dictionary** → defines each wall run in order from that origin
- **Executor** → reads both, walks the perimeter, and creates all Revit elements

## What is a Segment?

Each segment represents one straight run of the foundation outer face. Segments are walked in numeric order (segment_1, segment_2, ...). The executor advances the cursor along the outer face by the segment length, then offsets inward to the wall centerline to place the Revit wall.

A segment can create up to three Revit elements:
- A foundation wall
- A strip footing attached to that wall
- A cut wall above the foundation wall top

Setting `has_wall`, `has_footing`, and `has_cut_wall` all to `False` makes the segment a geometry-walk-only step — the cursor advances but no Revit element is created. This is useful for tracing corners at thickness transitions.

## What is a Strip Footing?

A strip footing is a `WallFoundation` element attached to the bottom of a foundation wall. Width and thickness are defined per segment in inches. Strip footings are always concrete regardless of the wall material.

## What is a Cut Wall?

A cut wall is an extension of the foundation wall above the foundation top, from the top of the foundation wall up to the underside of the floor finish (including mudsill thickness). It is narrower than the foundation wall by the joist bearing width.

cut wall thickness = wall_thickness_in - joist_bearing_in

The cut wall creates the joist bearing pocket where floor joists rest on the foundation.

## Schema

```python
segments_dict = {
    "segment_n": {
        # GEOMETRY
        "axis":               "x" or "y",  # direction segment runs
        "direction":          "+" or "-",  # sign along axis
        "length_variable_ft": float,       # scaled by x_scale or y_scale
        "length_fixed_ft":    float,       # NOT scaled

        # VERTICAL
        "top_elevation_ft":   float,  # wall top elevation from Level 0 (ft)
        "height_ft":          float,  # wall height (ft); bottom = top - height

        # FOUNDATION WALL
        "wall_thickness_in":  float,   # inches
        "wall_material":      string,  # "concrete" or "concrete_block"
        "has_wall":           boolean,

        # STRIP FOOTING
        "has_footing":           boolean,
        "footing_width_in":      float,  # inches
        "footing_thickness_in":  float,  # inches

        # CUT WALL
        "has_cut_wall":      boolean,
        "joist_bearing_in":  float,   # inches — joist bearing width on foundation wall
        "cut_wall_material": string,  # "concrete" or "concrete_block"
    },
}
```