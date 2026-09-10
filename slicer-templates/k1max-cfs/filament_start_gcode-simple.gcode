;filament start gcode
{if (position[2] > first_layer_height) }
M104 S[nozzle_temperature]
{else}
M104 S[first_layer_temperature]
{endif}