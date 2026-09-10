# Fix: E0500 key2586 — "Move out of gcode print range" after CFS filament change

## Symptom

Multi-color print on K1 Max (CFS kit) aborts at every filament change.
Creality screen shows `E0500 key2586 Unknown exception`.

- Screen fault log (`/usr/data/creality/userdata/log/master-server.log`):
  `error = 500, code = 2586, msg = Move out of gcode print range`
- Klippy log (`/usr/data/printer_data/logs/klippy.log`):
  `virtual_sdcard:check_gcode_print_range: Y value:345.000000  gcode_max_y:295.000000`

## Root cause

Creality Print's CFS `filament_start_gcode` template contains
`G1 X205 Y345 F20000`. Y=345 is only valid on 350 mm printers (K2 Plus);
the K1 Max gcode Y limit is 295 (physical max 307.5). The printer correctly
refuses the move right after a tool change, killing the print. The cutter
itself works — cut sensor events fire normally — the abort just happens
immediately after the change, which makes it look like the cutter sequence
failed.

Known bug affecting all 300 mm K1-series printers with the CFS upgrade
(K1, K1 Max, K1C, K1 SE). Template documented at
https://wiki.creality.com/en/software/6-0/t-command

## Fix (in Creality Print, per filament profile)

1. Open **Filament Settings** for every filament used in the multi-color
   print (e.g. *CR-PLA Carbon @Creality K1 Max 0.4 nozzle*).
2. Go to **Advanced -> Filament start G-code**.
3. Find `G1 X205 Y345 F20000` — it appears **twice** (both branches of the
   `{if ...}` template).
4. Change `Y345` to `Y290`, or delete the `G1 X205 Y345 F20000` line
   entirely (it is only a park move; the next wipe move `X154.2 Y262.5`
   is in range).
5. **Save as a custom preset** — bundled/cloud presets are read-only and
   would overwrite the edit on sync.
6. Repeat for each filament profile in the print job, then re-slice and
   reprint.

Nothing on the printer needs to change.

## Notes

- In-place edit applied on printer 2026-09-11 ~05:43: all 4 occurrences of
  `X205 Y345 F20000` replaced with `X205 Y290 F20000` in
  `Drawer - long.stl_PLA-CF_4h30m53s.gcode` (same byte length, file size
  unchanged at 5725806, so the pause/resume position 229397 stays valid).
  Backup kept at `Drawer - long.stl_PLA-CF_4h30m53s.gcode.bak-20260911`
  on the printer. Full-file scan confirmed those 4 lines were the only
  out-of-range moves. Resume via the screen's continue-print; the PLA-CF
  tool change had already completed before the abort.

- Verified on printer 2026-09-11: cut sensor events fire normally
  (`CUT SENSOR STATE: 1 -> 0`); both failed prints died at the same gcode
  file position (229397) on toolchange #2 at the `G1 X205 Y345` move.
- The helper-script repo is NOT installed on this printer (stock CFS
  config intact), so the earlier repo merge did not affect printer
  behavior.
- Local commit `545e92e` (opt-in `ADAPT_PURGE_MOD`, keeps heat soak +
  at-temp re-homing) is not yet pushed to qdzlug fork.
- Minor firmware quirk: screen sends `SET_HOTEND_FAN VALUE=1` at print
  start; klippy logs `key61: Unknown command` and continues. Harmless
  but worth watching.