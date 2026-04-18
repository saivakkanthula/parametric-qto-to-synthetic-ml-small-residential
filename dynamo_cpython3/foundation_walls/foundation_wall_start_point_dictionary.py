#Dynamo CPython3
#Foundation Walls - Start Point

import sys
import clr
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

#----- INPUTS------------------------------------------
x_scale = IN[0]
y_scale = IN[1]

#------ START POINT -----------------------------------
#Defines the origin of outer-face walk of the foundation walls
#Final Position = (x_fixed_ft + x_variable_ft * x_scale,
#                 y_fixed_ft + y_variable_ft * y_scale)


start_point_dict = {
                        "start_point":
                                        {
                                        "x_fixed_ft":0,
                                        "x_variable_ft":0,
                                        "y_fixed_ft":0,
                                        "y_variable_ft":0,
                                        }
                    
                    }
                    
                                    
                    
OUT  = start_point_dict