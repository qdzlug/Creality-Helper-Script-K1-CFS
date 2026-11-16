#!/usr/bin/env bash
# deploy_safe_motion_limits.sh — Install firmware-side print-time motion clamp
# (`safe-motion-limits.cfg`) onto MisterK1c and MisterK1max and reload Klipper
# via Moonraker's `POST /printer/firmware_restart` (only when idle).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="${SCRIPT_DIR}/../files/macros/safe-motion-limits.cfg"
LOCAL_MD5="$(md5sum "$CFG" | awk '{print $1}')"

PRINTERS=("${@:-192.168.212.13 192.168.213.79}")
PASSFILE="$(mktemp)"
trap 'rm -f "$PASSFILE"' EXIT
chmod 600 "$PASSFILE"
printf '%s\n' "${CREALITY_PASS:-creality_2023}" > "$PASSFILE"

for ip in $PRINTERS; do
  echo "=== Checking $ip ==="
  pstate="$(curl -sf --max-time 5 "http://$ip:7125/printer/objects/query?print_stats" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['status']['print_stats']['state'])")"
  if [[ "$pstate" == "printing" || "$pstate" == "paused" ]]; then
    echo "SKIP $ip: currently $pstate (refusing to restart mid-job)"
    continue
  fi

  echo "Uploading safe-motion-limits.cfg to $ip (state=$pstate)..."
  sshpass -f "$PASSFILE" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 -o PreferredAuthentications=password -o PubkeyAuthentication=no \
    "root@$ip" 'cat > /usr/data/printer_data/config/safe-motion-limits.cfg' < "$CFG"

  sshpass -f "$PASSFILE" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 -o PreferredAuthentications=password -o PubkeyAuthentication=no \
    "root@$ip" "
      set -e
      R_MD5=\$(md5sum /usr/data/printer_data/config/safe-motion-limits.cfg | awk '{print \$1}')
      [ \"\$R_MD5\" = \"$LOCAL_MD5\" ]
      mkdir -p /usr/data/printer_data/backups_hermes
      cp /usr/data/printer_data/config/printer.cfg \"/usr/data/printer_data/backups_hermes/printer.cfg.before-safe-motion-\$(date +%Y%m%d-%H%M%S)\"
      python3 - <<'PY'
p = '/usr/data/printer_data/config/printer.cfg'
txt = open(p).read()
inc = '[include safe-motion-limits.cfg]'
if inc not in txt:
    lines = txt.splitlines(True)
    idx = max(i for i, l in enumerate(lines) if l.startswith('[include '))
    lines.insert(idx + 1, inc + '\n')
    open(p, 'w').writelines(lines)
    print('Added', inc)
else:
    print('Already present:', inc)
PY
    "

  echo "Triggering Moonraker firmware_restart on $ip..."
  curl -sf --max-time 10 -X POST "http://$ip:7125/printer/firmware_restart" >/dev/null
done

echo "Waiting 15s for Klippy to become ready..."
sleep 15

for ip in $PRINTERS; do
  echo "=== Verifying $ip ==="
  curl -sf --max-time 10 "http://$ip:7125/printer/info" \
    | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(' ', r.get('hostname'), 'state=', r.get('state'))"
  curl -sf --max-time 10 -X POST "http://$ip:7125/printer/gcode/script?script=SAFE_MOTION_LIMITS" >/dev/null
  curl -sf --max-time 10 "http://$ip:7125/server/gcode_store?count=3" \
    | python3 -c "import sys,json; [print(' ', m['message']) for m in json.load(sys.stdin)['result']['gcode_store'][-2:]]"
done
