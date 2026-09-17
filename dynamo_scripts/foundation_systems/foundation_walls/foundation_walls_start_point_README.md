# Foundation Walls — Start Point

## What is the Start Point?

The start point defines the origin of the outer-face perimeter walk for the foundation walls.
The executor begins tracing foundation wall segments from this point, walking along the outer face of the foundation in the order segments are defined.

## Schema

```python
start_point_dict = {
    "start_point": {
        "x_fixed_ft":    float,  # NOT scaled — fixed X offset from project origin
        "x_variable_ft": float,  # scaled by x_scale at runtime
        "y_fixed_ft":    float,  # NOT scaled — fixed Y offset from project origin
        "y_variable_ft": float   # scaled by y_scale at runtime
    }
}
```

The final start position is computed as:

X = x_fixed_ft + x_variable_ft * x_scale
Y = y_fixed_ft + y_variable_ft * y_scale