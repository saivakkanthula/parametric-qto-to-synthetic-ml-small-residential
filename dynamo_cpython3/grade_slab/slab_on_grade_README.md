
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
   - Direction is given by (``"+"`` or ``"-"``)
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
