"""
Slab-on-Grade / Walkway Slab Generation
========================================

Generates slab-on-grade floors (and optional openings) using a
Manhattan (axis-aligned) segment-based layout system.

Geometry Principle
------------------
The slab outline is defined using a sequence of segments starting from a base
start point. Each segment moves along either the X or Y axis.

The raw outline is constructed as follows:

1. Start from the base start point::

       X = x_fixed_ft + x_variable_ft * x_scale
       Y = y_fixed_ft + y_variable_ft * y_scale

2. For each segment:
   - Move along its axis (``"x"`` or ``"y"``)
   - Direction is given by ``"+"`` or ``"-"``
   - Segment length is::

         length = length_fixed_ft + length_variable_ft * axis_scale

3. This produces a raw Manhattan outline (outer reference shape).

Offset Logic
------------
Each segment defines a point-based offset using ``x_offset_ft`` and
``y_offset_ft``. These offsets are applied to the **start point** of each
segment.

.. important::

   - Offsets modify the corner points, not segment lengths.
   - The start point of a segment is also the end point of the previous
     segment. Applying an offset therefore affects both the current segment
     start and the previous segment end.
   - Since the outline is closed, the last segment end connects back to the
     first segment start, so offsets also affect closure consistency.

``forms_outline`` Flag
----------------------
Each segment carries a ``forms_outline`` boolean. Only segments where
``forms_outline`` is ``True`` are used to build the final slab boundary.

Openings
--------
Openings follow the same segment logic as the main slab. Each opening:

- has its own segment set,
- uses the **same** start-point reference as the parent floor,
- generates a closed profile, and
- is cut from the slab using Revit opening tools.

Notes
-----
- All units are in feet unless otherwise specified.
- All offsets must be provided with the correct sign.
- The caller is responsible for the geometric correctness of the input.
"""

# ---------------------------------------------------------------------------
# Inputs (wired from Dynamo)
# ---------------------------------------------------------------------------

x_scale = IN[0]
y_scale = IN[1]

# ---------------------------------------------------------------------------
# Floor dictionary
# ---------------------------------------------------------------------------

slab_on_grade_floors = {

    "floor_1": {

        # --- Floor properties ---
        "level":        None,   # Revit Level object for slab placement
        "thickness_ft": 0,      # Slab thickness (ft)
        "has_openings": False,  # Set True if opening sub-dicts are defined below

        # --- Start point ---
        # Absolute origin of the segment chain.
        # Final position: X = x_fixed_ft + x_variable_ft * x_scale
        #                 Y = y_fixed_ft + y_variable_ft * y_scale
        "start_point": {
            "x_fixed_ft":    0,  # Fixed X component of start point (ft)
            "x_variable_ft": 0,  # Scaled X component of start point (ft)
            "y_fixed_ft":    0,  # Fixed Y component of start point (ft)
            "y_variable_ft": 0,  # Scaled Y component of start point (ft)
        },

        # --- Main outline segments ---
        # Segments are traversed in key order to build the closed outline.
        # Each segment moves from the previous end point along one axis.
        "segments": {

            "segment_1": {
                "axis":               "x",   # Movement axis: "x" or "y"
                "direction":          "+",   # Movement direction: "+" or "-"
                "length_fixed_ft":    0,     # Fixed component of segment length (ft)
                "length_variable_ft": 0,     # Variable component, scaled by axis scale (ft)
                "x_offset_ft":        0,     # X correction applied to this segment's start point (ft)
                "y_offset_ft":        0,     # Y correction applied to this segment's start point (ft)
                "forms_outline":      True,  # Include in final slab boundary
            },

            # Add more segments as needed...

        },

        # --- Openings ---
        # Each opening uses the same start_point reference as the parent floor.
        # Remove opening sub-dicts entirely if has_openings is False.
        "opening_1": {

            "segment_1": {
                "axis":               "x",   # Movement axis: "x" or "y"
                "direction":          "+",   # Movement direction: "+" or "-"
                "length_fixed_ft":    0,     # Fixed component of segment length (ft)
                "length_variable_ft": 0,     # Variable component, scaled by axis scale (ft)
                "x_offset_ft":        0,     # X correction applied to this segment's start point (ft)
                "y_offset_ft":        0,     # Y correction applied to this segment's start point (ft)
                "forms_outline":      True,  # Include in final opening boundary
            },

            # Add more segments as needed...

        },

        # Add more openings as needed: "opening_2": { ... }

    },

    # Add more floors as needed: "floor_2": { ... }

}

# ---------------------------------------------------------------------------
# Dynamo output
# ---------------------------------------------------------------------------

OUT = slab_on_grade_floors
