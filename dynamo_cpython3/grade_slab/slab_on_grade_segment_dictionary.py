
# ---------------------------------------------------------------------------
# Inputs (wired from Dynamo)
# ---------------------------------------------------------------------------

x_scale = IN[0]
y_scale = IN[1]
#Any other as needed

# ---------------------------------------------------------------------------
# Floor dictionary 
# ---------------------------------------------------------------------------

slab_on_grade_floors = {

    "floor_1": {

        # --- Floor properties ---
        "level":        RevitLevel,   # Revit Level object for slab placement
        "thickness_ft": float,      # Slab thickness (ft)
        "has_openings": boolean,  # Set True if opening sub-dicts are defined below

        # --- Start point ---
        # Absolute origin of the segment chain.
        # Final position: X = x_fixed_ft + x_variable_ft * x_scale
        #                 Y = y_fixed_ft + y_variable_ft * y_scale
        "start_point": {
            "x_fixed_ft":    float,  # Fixed X component of start point (ft)
            "x_variable_ft": float,  # Scaled X component of start point (ft)
            "y_fixed_ft":    float,  # Fixed Y component of start point (ft)
            "y_variable_ft": float,  # Scaled Y component of start point (ft)
        },

        # --- Main outline segments ---
        # Segments are traversed in key order to build the closed outline.
        # Each segment moves from the previous end point along one axis.
        "segments": {

            "segment_1": {
                "axis":               Literal,   # Movement axis: "x" or "y"
                "direction":          Literal,   # Movement direction: "+" or "-"
                "length_fixed_ft":    float,     # Fixed component of segment length (ft)
                "length_variable_ft": float,     # Variable component, scaled by axis scale (ft)
                "x_offset_ft":        float,     # X correction applied to this segment's start point (ft)
                "y_offset_ft":        float,     # Y correction applied to this segment's start point (ft)
                "forms_outline":      boolean,  # Include in final slab boundary
            },

            # Add more segments as needed...

        },

        # --- Openings ---
        # Each opening uses the same start_point reference as the parent floor.
        # Remove opening sub-dicts entirely if has_openings is False.
        "opening_1": {

            "segment_1": {
                "axis":               Literal,   # Movement axis: "x" or "y"
                "direction":          Literal,   # Movement direction: "+" or "-"
                "length_fixed_ft":    float,     # Fixed component of segment length (ft)
                "length_variable_ft": float,     # Variable component, scaled by axis scale (ft)
                "x_offset_ft":        float,     # X correction applied to this segment's start point (ft)
                "y_offset_ft":        float,     # Y correction applied to this segment's start point (ft)
                "forms_outline":      boolean,  # Include in final opening boundary
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
