# K1C "mid-print sideways jump" (lost steps / layer shift) — settings

Symptom: the job prints fine for 20–160 min, then the toolhead jumps sideways and keeps
printing offset — plastic keeps flowing, no fault on the screen, nothing in `klippy.log`.
Confirmed on `MisterK1c` (192.168.212.13): the upper section is displaced relative to the
layers below, so this is real step loss, not a pause-park move.

**A skipped step writes NO log entry** (no encoder on X/Y). A clean fault history does not
clear the print. `toolhead.stalls` is Klipper's *host print-queue* stall, not step loss.

## Where the load comes from

`Halloween_Cyber_Pumpkin_10262330.gcode` (K1C 0.20mm Standard, Creality_Cloud_Slicer
V7.3.0.0): 571 layers, 114.2 mm, 108 mm wide, 2 wall loops, 10 % grid infill, 418 tree
support blocks, 317 overhang walls, 76 bridges. Per-job motion demand:

| gcode field | value | note |
|---|---|---|
| `travel_speed` | 500 mm/s | 21 220 non-extruding moves at F30000 |
| `travel_acceleration` | 10000 mm/s² | 5 498 `SET_VELOCITY_LIMIT ACCEL=10000 … SQUARE_CORNER_VELOCITY=8` |
| `default_acceleration` | 10000 |
| `z_hop` | 0.4 mm | with `z_hop_types = Auto Lift` |
| `avoid_crossing_perimeters` | *not set* | travels cross the part |
| `slowdown_for_curled_perimeters` | 0 |
| `reduce_crossing_wall` | 0 |
| `retraction_length` / `speed` | 0.8 mm / 40 mm/s |

Printer motion limits (`printer.cfg`): `max_velocity 600`, `max_accel 20000`,
`max_accel_to_decel 20000`, `square_corner_velocity 5.0`. TMC2209 on X and Y:
`run_current 1.5`, `hold_current 1.0`, `stealthchop_threshold 0` (spreadCycle always — good,
no stealthChop torque collapse at speed). **No `[input_shaper]` section exists on this box**
(only `[resonance_tester]`), so there is no resonance compensation to soften the cornering.

## Recommended slice settings (0.20mm Standard @Creality K1C 0.4 nozzle)

| field in the gcode header | from | to |
|---|---|---|
| `travel_speed` | 500 | 250 |
| `travel_acceleration` | 10000 | 5000 |
| `default_acceleration` | 10000 | 5000 |
| `outer_wall_acceleration` | 3000 | 2500 |
| `z_hop` | 0.4 | 0.6 |
| `slowdown_for_curled_perimeters` | 0 | 1 |
| `avoid_crossing_perimeters` | unset | on (max detour 0 so it cannot lengthen travels) |
| `reduce_crossing_wall` | 0 | 1 |
| `sparse_infill_speed` | 270 | 220 |

UI labels differ between Creality Print and OrcaSlicer (both Orca-derived) — verify what
actually landed instead of trusting the checkbox:

```sh
grep -aE "^; (travel_speed|travel_acceleration|default_acceleration|z_hop|slowdown_for_curled_perimeters|avoid_crossing_perimeters|reduce_crossing_wall) =" FILE.gcode
grep -ac "^SET_VELOCITY_LIMIT ACCEL=10000" FILE.gcode      # want 0
awk '/^G1/&&/F30000/&&!/E[0-9.]/{c++} END{print c+0}' FILE.gcode   # want 0
```

## Patching an already-sliced file (no slicer needed)

Motion load can be cut in an existing gcode without touching extrusion, flow or geometry:
cap non-extruding `F30000` travel moves (500 → 250 mm/s), rewrite
`SET_VELOCITY_LIMIT ACCEL=10000 ACCEL_TO_DECEL=10000 SQUARE_CORNER_VELOCITY=8` →
`ACCEL=5000 ACCEL_TO_DECEL=5000 SQUARE_CORNER_VELOCITY=5`, and leave every line carrying an
`E` value alone. Proof that only motion changed: the **sum of all E values must be
byte-identical** before and after (here 37943.7518 over 585 306 extrude commands).

Patched result: `Halloween_Cyber_Pumpkin_10262330_SLOW.gcode` on the printer
(md5 `fb64890e34e055b15ebb9d0e1c6b4e42`).

## This is mitigation, not the root cause

Repeatable step loss at *varying* Z on one file means load/friction, not a fixed model
feature. Ordered by likelihood on a CoreXY K1C:

1. **XY belt tension** — a belt that can jump a tooth. Tension both, retest.
2. **Pulley grub screws** on both X and Y motors — a loose grub screw slips under torque
   reversal and produces exactly this jump.
3. **Rail friction** — clean + lubricated (done 2026-11-01); dry rails raise the torque needed.
4. **CFS PTFE tube / cable chain** going taut at the extremes of travel and yanking the head.
5. **Nozzle snag** on a curled edge or blob — the anti-snag settings above are the fix.

If it fails again on the patched file at the same kind of place, the belts/grub screws are
the cause, not the motion profile.
