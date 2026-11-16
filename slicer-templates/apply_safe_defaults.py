#!/usr/bin/env python3
"""apply_safe_defaults.py — Install anti-layer-shift ("Safe") machine & process
defaults for K1C and K1 Max in Creality Print 7.x and OrcaSlicer 2.x (macOS/Linux).

Applies the lost-step / anti-snag mitigations:
  * travel_speed = 250 mm/s (from 500)
  * travel_acceleration = 5000 mm/s^2 (from 10000)
  * default_acceleration = 5000 mm/s^2 (from 10000)
  * outer_wall_acceleration <= 2500 mm/s^2, inner_wall_acceleration <= 3000 mm/s^2
  * jerk / square_corner_velocity = 5 mm/s across all moves (K1 Max stock is 20!)
  * z_hop = 0.6 mm (Auto Lift) on machine profiles (from 0.4 mm)
  * sparse_infill_pattern = gyroid (replaces self-crossing grid)
  * sparse_infill_speed <= 220 mm/s
  * reduce_crossing_wall = 1, max_travel_detour_distance = 0
  * slowdown_for_curled_perimeters = 1

Idempotent, creates timestamped backups before writing, and uses deterministic
setting_ids across hosts so Creality Cloud sync sees identical preset IDs.
"""

import glob
import hashlib
import json
import os
import shutil
import sys
import time
import uuid

NOW = int(time.time())
STAMP = time.strftime("%Y%m%d-%H%M%S")

MACHINE_SAFE_OVERRIDES = {
    "z_hop": ["0.6"],
    "z_hop_types": ["Auto Lift"],
    "machine_max_acceleration_travel": ["5000", "5000"],
    "machine_max_acceleration_extruding": ["10000", "10000"],
    "machine_max_acceleration_x": ["10000", "10000"],
    "machine_max_acceleration_y": ["10000", "10000"],
    "machine_max_jerk_x": ["5", "5"],
    "machine_max_jerk_y": ["5", "5"],
}


def build_process_overrides(parent_json):
    def cap_int(key, ceiling):
        raw = parent_json.get(key)
        if isinstance(raw, list):
            raw = raw[0] if raw else str(ceiling)
        try:
            return str(min(int(float(raw)), ceiling))
        except Exception:
            return str(ceiling)

    return {
        "travel_speed": "250",
        "travel_acceleration": "5000",
        "default_acceleration": "5000",
        "outer_wall_acceleration": cap_int("outer_wall_acceleration", 2500),
        "inner_wall_acceleration": cap_int("inner_wall_acceleration", 3000),
        "sparse_infill_speed": cap_int("sparse_infill_speed", 220),
        "sparse_infill_pattern": "gyroid",
        "slowdown_for_curled_perimeters": "1",
        "reduce_crossing_wall": "1",
        "max_travel_detour_distance": "0",
        "default_jerk": "5",
        "travel_jerk": "5",
        "infill_jerk": "5",
        "outer_wall_jerk": "5",
        "inner_wall_jerk": "5",
        "top_surface_jerk": "5",
        "initial_layer_jerk": "5",
    }


def cp_setting_id(preset_name):
    return "6a" + hashlib.sha256(("hermes-cp:" + preset_name).encode()).hexdigest()[:22]


def orca_setting_id(preset_name):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, "hermes-orca:" + preset_name))


def write_info(path, user_id, setting_id, base_id):
    content = (
        f"sync_info = \n"
        f"user_id = {user_id}\n"
        f"setting_id = {setting_id}\n"
        f"base_id = {base_id}\n"
        f"updated_time = {NOW}\n"
    )
    with open(path, "w") as f:
        f.write(content)


def backup_file(src, backup_root, base_dir):
    if not os.path.exists(src):
        return
    rel = os.path.relpath(src, base_dir)
    dst = os.path.join(backup_root, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def apply_creality_print(cp_dir):
    if not os.path.isdir(cp_dir):
        print(f"[Creality Print] Not found at {cp_dir}, skipping.")
        return

    sys_dir = os.path.join(cp_dir, "system", "Creality")
    user_root = os.path.join(cp_dir, "user")
    uids = [
        d for d in os.listdir(user_root)
        if os.path.isdir(os.path.join(user_root, d)) and d.isdigit()
    ]
    if not uids:
        uids = ["default"]

    backup_root = os.path.join(cp_dir, "backups_hermes", f"safe_defaults_{STAMP}")
    os.makedirs(backup_root, exist_ok=True)

    pairs = [
        ("Creality K1C 0.4 nozzle", "0.20mm Standard @Creality K1C 0.4 nozzle"),
        ("Creality K1C_CFS-C 0.4 nozzle", "0.20mm Standard @Creality K1C_CFS-C 0.4 nozzle"),
        ("Creality K1C 0.6 nozzle", "0.30mm Standard @Creality K1C 0.6 nozzle"),
        ("Creality K1 Max 0.4 nozzle", "0.20mm Standard @Creality K1 Max 0.4 nozzle"),
        ("Creality K1 Max_CFS-C 0.4 nozzle", "0.20mm Standard @Creality K1 Max_CFS-C 0.4 nozzle"),
        ("Creality K1 Max 0.6 nozzle", "0.30mm Standard @Creality K1 Max 0.6 nozzle"),
    ]

    machine_to_safe_machine = {}
    machine_to_safe_process = {}

    for uid in uids:
        u_dir = os.path.join(user_root, uid)
        os.makedirs(os.path.join(u_dir, "machine"), exist_ok=True)
        os.makedirs(os.path.join(u_dir, "process"), exist_ok=True)

        for sys_m_name, sys_p_name in pairs:
            sys_m_path = os.path.join(sys_dir, "machine", f"{sys_m_name}.json")
            sys_p_path = os.path.join(sys_dir, "process", f"{sys_p_name}.json")
            if not (os.path.isfile(sys_m_path) and os.path.isfile(sys_p_path)):
                continue

            sys_m = json.load(open(sys_m_path))
            sys_p = json.load(open(sys_p_path))

            safe_m_name = f"{sys_m_name} (Safe)"
            safe_p_name = sys_p_name.replace(" Standard @", " Standard Safe @")

            machine_to_safe_machine[sys_m_name] = safe_m_name
            machine_to_safe_process[sys_m_name] = safe_p_name
            machine_to_safe_process[safe_m_name] = safe_p_name

            # 1. Write Safe Machine preset
            m_json_path = os.path.join(u_dir, "machine", f"{safe_m_name}.json")
            m_info_path = os.path.join(u_dir, "machine", f"{safe_m_name}.info")
            backup_file(m_json_path, backup_root, cp_dir)
            backup_file(m_info_path, backup_root, cp_dir)

            m_base_id = sys_m.get("setting_id", "13140")
            m_doc = {
                "base_id": m_base_id,
                "from": "User",
                "inherits": sys_m_name,
                "is_custom_defined": "0",
                "name": safe_m_name,
                "printer_settings_id": safe_m_name,
                "version": "26.10.10.9",
            }
            m_doc.update(MACHINE_SAFE_OVERRIDES)
            with open(m_json_path, "w") as f:
                json.dump(m_doc, f, indent=4, sort_keys=True)
            write_info(m_info_path, uid, cp_setting_id(safe_m_name), m_base_id)

            # 2. Write Safe Process preset
            p_json_path = os.path.join(u_dir, "process", f"{safe_p_name}.json")
            p_info_path = os.path.join(u_dir, "process", f"{safe_p_name}.info")
            backup_file(p_json_path, backup_root, cp_dir)
            backup_file(p_info_path, backup_root, cp_dir)

            p_base_id = sys_p.get("setting_id", "GP004")
            p_doc = {
                "base_id": p_base_id,
                "compatible_printers": [sys_m_name, safe_m_name],
                "from": "User",
                "inherits": sys_p_name,
                "is_custom_defined": "0",
                "name": safe_p_name,
                "print_settings_id": safe_p_name,
                "version": "26.10.10.9",
            }
            p_doc.update(build_process_overrides(sys_p))
            with open(p_json_path, "w") as f:
                json.dump(p_doc, f, indent=4, sort_keys=True)
            write_info(p_info_path, uid, cp_setting_id(safe_p_name), p_base_id)

        # Update sync_data.json
        sd_path = os.path.join(u_dir, "sync_data", "sync_data.json")
        if os.path.isfile(sd_path):
            backup_file(sd_path, backup_root, cp_dir)
            sd = json.load(open(sd_path))
            cur_m = sd.get("current_machine", "")
            if cur_m in machine_to_safe_machine:
                sd["current_machine"] = machine_to_safe_machine[cur_m]
            machines_list = sd.get("machines", [])
            by_name = {entry.get("machine"): entry for entry in machines_list if isinstance(entry, dict)}
            for stock_m, safe_m in machine_to_safe_machine.items():
                safe_p = machine_to_safe_process[stock_m]
                if stock_m in by_name:
                    by_name[stock_m]["process"] = safe_p
                    cloned = dict(by_name[stock_m])
                    cloned["machine"] = safe_m
                    cloned["process"] = safe_p
                    by_name[safe_m] = cloned
                else:
                    default_fil = f"Hyper PLA @{stock_m}"
                    by_name[stock_m] = {"curr_bed_type": "3", "filament_01": default_fil, "machine": stock_m, "process": safe_p}
                    by_name[safe_m] = {"curr_bed_type": "3", "filament_01": default_fil, "machine": safe_m, "process": safe_p}
            sd["machines"] = sorted(by_name.values(), key=lambda x: x.get("machine", ""))
            sd["update_time"] = str(NOW)
            with open(sd_path, "w") as f:
                json.dump(sd, f, indent=4, sort_keys=True)

    # Update Creality.conf
    conf_path = os.path.join(cp_dir, "Creality.conf")
    if os.path.isfile(conf_path):
        backup_file(conf_path, backup_root, cp_dir)
        conf = json.load(open(conf_path))
        presets = conf.get("presets", {})
        cur_m = presets.get("machine", "")
        if cur_m in machine_to_safe_machine:
            presets["machine"] = machine_to_safe_machine[cur_m]
            presets["process"] = machine_to_safe_process[cur_m]
        elif cur_m in machine_to_safe_process:
            presets["process"] = machine_to_safe_process[cur_m]
        conf["presets"] = presets

        op_list = conf.get("orca_presets", [])
        by_name = {entry.get("machine"): entry for entry in op_list if isinstance(entry, dict)}
        for stock_m, safe_m in machine_to_safe_machine.items():
            safe_p = machine_to_safe_process[stock_m]
            if stock_m in by_name:
                by_name[stock_m]["process"] = safe_p
                cloned = dict(by_name[stock_m])
                cloned["machine"] = safe_m
                cloned["process"] = safe_p
                by_name[safe_m] = cloned
            else:
                default_fil = f"Hyper PLA @{stock_m}"
                by_name[stock_m] = {"curr_bed_type": "3", "filament_01": default_fil, "machine": stock_m, "process": safe_p}
                by_name[safe_m] = {"curr_bed_type": "3", "filament_01": default_fil, "machine": safe_m, "process": safe_p}
        conf["orca_presets"] = sorted(by_name.values(), key=lambda x: x.get("machine", ""))
        with open(conf_path, "w") as f:
            json.dump(conf, f, indent=4, sort_keys=True)

    print(
        f"[Creality Print] Installed {len(machine_to_safe_machine)} Safe machine + process presets "
        f"(active machine={conf.get('presets', {}).get('machine')!r}, "
        f"process={conf.get('presets', {}).get('process')!r}). Backup: {backup_root}"
    )


def apply_orcaslicer(orca_dir):
    if not os.path.isdir(orca_dir):
        print(f"[OrcaSlicer] Not found at {orca_dir}, skipping.")
        return

    conf_path = os.path.join(orca_dir, "OrcaSlicer.conf")
    if not os.path.isfile(conf_path):
        print(f"[OrcaSlicer] No OrcaSlicer.conf at {conf_path}, skipping.")
        return

    backup_root = os.path.join(orca_dir, "backups_hermes", f"safe_defaults_{STAMP}")
    os.makedirs(backup_root, exist_ok=True)
    backup_file(conf_path, backup_root, orca_dir)

    conf = json.load(open(conf_path))
    uid = conf.get("app", {}).get("preset_folder") or "default"
    u_dir = os.path.join(orca_dir, "user", uid)
    os.makedirs(os.path.join(u_dir, "machine"), exist_ok=True)
    os.makedirs(os.path.join(u_dir, "process"), exist_ok=True)

    # Patch existing MisterK1c & MisterK1Max user machine profiles in-place
    user_machines = [
        ("MisterK1c", "Creality K1_CFS-C 0.4 nozzle", "0.20mm Standard @Creality K1_CFS-C 0.4 nozzle"),
        ("MisterK1Max", "Creality K1 Max_CFS-C 0.4 nozzle", "0.20mm Standard @Creality K1 Max_CFS-C 0.4 nozzle"),
    ]

    machine_to_safe_proc = {}

    for m_name, expected_parent, sys_p_name in user_machines:
        m_json_path = os.path.join(u_dir, "machine", f"{m_name}.json")
        m_info_path = os.path.join(u_dir, "machine", f"{m_name}.info")
        if os.path.isfile(m_json_path):
            backup_file(m_json_path, backup_root, orca_dir)
            backup_file(m_info_path, backup_root, orca_dir)
            m_doc = json.load(open(m_json_path))
            parent_m_name = m_doc.get("inherits", expected_parent)
            m_doc.update(MACHINE_SAFE_OVERRIDES)
            with open(m_json_path, "w") as f:
                json.dump(m_doc, f, indent="\t", sort_keys=True)
            if os.path.isfile(m_info_path):
                lines = []
                for line in open(m_info_path):
                    if line.startswith("updated_time ="):
                        lines.append(f"updated_time = {NOW}\n")
                    else:
                        lines.append(line)
                with open(m_info_path, "w") as f:
                    f.writelines(lines)
        else:
            parent_m_name = expected_parent

        # Locate system process preset
        matches = glob.glob(os.path.join(orca_dir, "system", "**", "process", f"{sys_p_name}.json"), recursive=True)
        if not matches:
            continue
        sys_p = json.load(open(matches[0]))
        p_base_id = sys_p.get("setting_id", "")

        safe_p_name = f"0.20mm Standard Safe @{m_name}"
        p_json_path = os.path.join(u_dir, "process", f"{safe_p_name}.json")
        p_info_path = os.path.join(u_dir, "process", f"{safe_p_name}.info")
        backup_file(p_json_path, backup_root, orca_dir)
        backup_file(p_info_path, backup_root, orca_dir)

        p_doc = {
            "compatible_printers": [parent_m_name, m_name],
            "from": "User",
            "inherits": sys_p_name,
            "is_custom_defined": "0",
            "name": safe_p_name,
            "print_settings_id": safe_p_name,
            "version": m_doc.get("version", "2.3.2.75") if os.path.isfile(m_json_path) else "2.3.2.75",
        }
        p_doc.update(build_process_overrides(sys_p))
        with open(p_json_path, "w") as f:
            json.dump(p_doc, f, indent="\t", sort_keys=True)
        write_info(p_info_path, uid, orca_setting_id(safe_p_name), p_base_id)

        machine_to_safe_proc[m_name] = safe_p_name
        machine_to_safe_proc[parent_m_name] = safe_p_name

    # Update OrcaSlicer.conf orca_presets & presets
    op_list = conf.get("orca_presets", [])
    for entry in op_list:
        if isinstance(entry, dict) and entry.get("machine") in machine_to_safe_proc:
            entry["process"] = machine_to_safe_proc[entry["machine"]]
    conf["orca_presets"] = op_list
    if isinstance(conf.get("presets"), dict):
        cur_m = conf["presets"].get("machine")
        if cur_m in machine_to_safe_proc:
            conf["presets"]["process"] = machine_to_safe_proc[cur_m]

    with open(conf_path, "w") as f:
        json.dump(conf, f, indent="\t", sort_keys=True)

    print(
        f"[OrcaSlicer] Patched user machines {list(machine_to_safe_proc.keys())} and bound "
        f"0.20mm Standard Safe defaults. Backup: {backup_root}"
    )


def main():
    if sys.platform == "darwin":
        cp_default = os.path.expanduser("~/Library/Application Support/Creality/Creality Print/7.3")
        orca_default = os.path.expanduser("~/Library/Application Support/OrcaSlicer")
    else:
        cp_default = os.path.expanduser("~/.config/Creality/Creality Print/7.3")
        orca_default = os.path.expanduser("~/.config/OrcaSlicer")

    apply_creality_print(cp_default)
    apply_orcaslicer(orca_default)


if __name__ == "__main__":
    main()
