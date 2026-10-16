#!/usr/bin/env bash
# Re-records only the "keep the median run" step of Part I (logs/I_median.log), using the
# fixed command from run_experiment.sh. Needs the sender container from the main run.
# usage (in ~/sig-lab):  bash tools/redo_median_step.sh
set -u
cd "$(dirname "$0")/.." || exit 1
docker start sender >/dev/null || { echo "sender container not found - run ./run_experiment.sh instead"; exit 1; }
LOG=logs/I_median.log
: > "$LOG"
c() { local ctr=$1; shift; echo "root@$ctr:/lab# $*" | tee -a "$LOG"
      docker exec -e COLUMNS=150 "$ctr" bash -c "$*" 2>&1 | tee -a "$LOG"; echo | tee -a "$LOG" >/dev/null; }

c sender 'cd /lab && for r in 1 2 3; do echo "run $r: sum of mean_ms = $(awk -F, '"'"'NR>1{s+=$5} END{printf "%.2f", s}'"'"' results_run$r.csv)"; done'
MED=$(for r in 1 2 3; do echo "$(awk -F, 'NR>1{s+=$5} END{print s}' sender/results_run$r.csv) $r"; done | sort -n | sed -n 2p | cut -d' ' -f2)
c sender "cd /lab && cp results_run$MED.csv results.csv && cat results.csv"
echo "re-recorded $LOG (median run = $MED)"
