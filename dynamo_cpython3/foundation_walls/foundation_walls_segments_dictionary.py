#Dynamo CPython3
#Foundation Walls - Segments Dictionary

import sys
import clr

clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

clr.AddReference("RevitNodes")
import Revit

#------ INPUTS -------
x_scale = IN[0]
y_scale = IN[1]

#Any Other INPUTS as Required

#-------- SEGMENTS DICTIONARY ----------

segments_dict = {

                    "segment_1": 
                                {
                                    # GEOMETRY
                                    "axis":               "x",    # "x" or "y" — direction segment runs
                                    "direction":          "+",    # "+" or "-" — sign along axis
                                    "length_variable_ft": 0.0,    # scaled by x_scale or y_scale
                                    "length_fixed_ft":    0.0,    # NOT scaled

                                    # VERTICAL
                                    "top_elevation_ft":   0.0,    # wall top elevation from Level 0 (ft)
                                    "height_ft":          0.0,    # wall height (ft); bottom = top - height

                                    # FOUNDATION WALL
                                    "wall_thickness_in":  0,      # inches
                                    "wall_material":      "string",  # "concrete" or "concrete_block"
                                    "has_wall":           bool,     #True or False

                                    # STRIP FOOTING - Always Concrete
                                    "has_footing":           bool, #True or False
                                    "footing_width_in":      0,  # inches
                                    "footing_thickness_in":  0,   # inches

                                    # CUT WALL (joist bearing pocket)
                                    "has_cut_wall":       bool,   #True or False
                                    "joist_bearing_in":   0,      # inches - width of joist bearing on the foundation wall
                                    "cut_wall_material": "string",  # "concrete" or "concrete_block"
                                },

                }
OUT = segments_dict