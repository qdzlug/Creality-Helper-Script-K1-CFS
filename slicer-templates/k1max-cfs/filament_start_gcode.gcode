;filament start gcode
{if (position[2] > first_layer_height) }
M104 S[nozzle_temperature]
{else}
M104 S[first_layer_temperature]
{endif}

{if(initial_extruder != current_extruder || position[2] > first_layer_height)}
{if (position[2] +0.4  < printable_height) }
G2 Z{position[2]  + 0.4} I0.86 J0.86 P1 F10000 ; spiral lift a little from second lift
G1 X205 Y290 F20000
G1 Z{position[2] } F1200
{else}
G1 X205 Y290 F20000
{endif}
{endif}