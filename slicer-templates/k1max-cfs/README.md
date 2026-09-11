# Creality K1 Max + CFS slicer templates (fixed)

Extracted from a real Creality Print 7.2.0.5226 K1 Max CFS job
(`Drawer - long.stl_PLA-CF_4h30m53s.gcode` header). This is the form the
K1 Max template takes — each piece lives in a separate slicer profile
field. The `[square_brackets]` and `{curly_braces}` placeholders are
OrcaSlicer/Creality Print template variables — keep them as-is.

## The one bug to know about

Creality ships the *filament_start_gcode* preset with a park move to
`G1 X205 Y345 F20000`. Y=345 is only valid on 350 mm printers (K2 Plus).
The K1 Max gcode Y limit is **295**, so every toolchange that runs this
template dies with `E0500 key2586 / CY2586 "Move out of gcode print
range"` right after the CFS filament change. All templates here are
already fixed to **`G1 X205 Y290 F20000`** (Y290 keeps the front-park
intent while staying in range). Affects every 300 mm K1-series printer
with the CFS kit (K1, K1 Max, K1C, K1 SE).

## Where each file goes

| File | Slicer field | Profile type |
|------|--------------|--------------|
| `machine_start_gcode.gcode` | Machine start G-code | Printer settings |
| `machine_end_gcode.gcode` | Machine end G-code | Printer settings |
| `machine_pause_gcode.gcode` | Machine pause G-code | Printer settings |
| `change_filament_gcode.gcode` | Change filament G-code | Print settings |
| `filament_start_gcode.gcode` | Filament start G-code (full variant — for filaments used as a *later* tool in multi-color jobs, e.g. CR-PLA Carbon) | Filament settings → Advanced |
| `filament_start_gcode-simple.gcode` | Filament start G-code (simple variant — temp-only, e.g. Hyper PLA / Soleyin Ultra PLA) | Filament settings → Advanced |
| `filament_end_gcode.gcode` | Filament end G-code | Filament settings → Advanced |
| `before_layer_change_gcode.gcode` | Before layer change G-code | Print settings |
| `layer_change_gcode.gcode` | Layer change G-code | Print settings |

## Coordinate map (must match the printer's box.cfg)

- `G1 X38 Y230` in *change_filament_gcode* = pre-cut position
  (`pre_cut_pos_x: 38`, `pre_cut_pos_y: 230` in the printer's `box.cfg`)
- `G1 X205 Y290` in *filament_start_gcode* = post-change park; must stay
  within X/Y ≤ 295 on 300 mm beds
- Everything at Y ≥ 305.5 (flush/extrude/cut positions) is handled by the
  printer's box module internally and must NOT appear in slicer gcode

## Applying / pushing to other systems

1. Open the profile in Creality Print (or OrcaSlicer), replace the field
   contents with these files, save as a **custom preset** (bundled and
   cloud presets are read-only and would overwrite local edits on sync).
2. Do this for **every filament profile** used in multi-color prints —
   Creality's CFS presets each carry their own copy of
   `filament_start_gcode`.
3. Re-slice and verify: in the slicer preview (travel moves visible),
   no toolchange travel should exceed Y295.

> Requires the KAMP module (with the opt-in-purge `ADAPT_PURGE_MOD`
> variant) installed on the printer — `machine_start_gcode` calls
> `ADAPT_PURGE_MOD` right after the initial `T` command, once the CFS has
> loaded and flushed filament. Without that helper-script module the
> purge call is an unknown command; with stock START_PRINT (purge inline)
> the `ADAPT_PURGE_MOD` line should be removed.

## Verification

On a sliced file, check the header:
`grep -c 'Y345' file.gcode` must return 0 for K1 Max.