# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# NPC_selection_test_1.py
# Created on: 2016-10-24 14:03:24.00000
#   (generated by ArcGIS/ModelBuilder)
# Usage: selection_test_1 <Discrepancy_Layer> 
# Description: 
# ---------------------------------------------------------------------------

# Import arcpy module
import arcpy

# Script arguments
Discrepancy_Layer = arcpy.GetParameterAsText(0)

# Local variables:
Output_Layer = ""
Output_Feature_Class__2_ = Output_Layer
Output_Layer__2_ = ""
Output_Feature_Class = Output_Layer__2_

# Process: Make Feature Layer
arcpy.MakeFeatureLayer_management(Discrepancy_Layer, Output_Layer, "TOWN = ' ' OR NAME = ' '", "", "")

# Process: Delete Features
arcpy.DeleteFeatures_management(Output_Layer)

# Process: Make Feature Layer (2)
arcpy.MakeFeatureLayer_management(Output_Feature_Class__2_, Output_Layer__2_, "", "", "")

# Process: Calculate Field
arcpy.CalculateField_management(Output_Layer__2_, "F_AREA", "!shape.area@acres!", "PYTHON", "")
