START_PRINT EXTRUDER_TEMP=[nozzle_temperature_initial_layer] BED_TEMP=[bed_temperature_initial_layer_single]
T[initial_no_support_extruder]
M204 S2000
M104 S[nozzle_temperature_initial_layer]
G1 Z3 F600
M83
G92 E0
G1 Z1 F600