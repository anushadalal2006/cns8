#!/usr/bin/env bash
# run_experiment.sh - runs Parts C5-I and Section 15 of Experiment 8 end to end and keeps a
# transcript of every command (prompt + output) in logs/. This repository folder plays the
# role of ~/sig-lab from the lab sheet (sender/ and receiver/ are mounted at /lab).
#
# usage:  STUDENT_UID=2024300032 ./run_experiment.sh      (image sig-lab:1.0 must exist, Step C4)
set -u
export STUDENT_UID=${STUDENT_UID:-2024300032}
LAB=$(cd "$(dirname "$0")" && pwd)
LOGS=$LAB/logs
mkdir -p "$LOGS"
cd "$LAB"

LOG=/dev/null
step() { LOG="$LOGS/$1.log"; : > "$LOG"; echo "=== $1 ==="; }
# host command: "user@host:~/sig-lab$ cmd"
h() { echo "anudalal25@anusha:~/sig-lab\$ $*" | tee -a "$LOG"; bash -c "$*" 2>&1 | tee -a "$LOG"; echo | tee -a "$LOG" >/dev/null; }
# container command: "root@<c>:/lab# cmd"
c() { local ctr=$1; shift; echo "root@$ctr:/lab# $*" | tee -a "$LOG"
      docker exec -e COLUMNS=150 "$ctr" bash -c "$*" 2>&1 | tee -a "$LOG"; echo | tee -a "$LOG" >/dev/null; }

# ---------------------------------------------------------------- clean start
docker rm -f sender receiver >/dev/null 2>&1
docker network rm sig-net >/dev/null 2>&1
rm -rf sender/keys sender/outbox sender/results*.csv sender/graphs sender/http_server.log \
       receiver/inbox receiver/keys receiver/outbox receiver/results*.csv graphs
cp sender/*.py receiver/                                    # Step D2: common.py (+ programs) on both sides

# ---------------------------------------------------------------- Part C
step C4_image
h "docker images sig-lab"

step C5_network
h "docker network create sig-net"
h "docker network ls"
h "docker network inspect sig-net"

step C6_containers
h "export STUDENT_UID=$STUDENT_UID"
h "docker run -dit --name sender   --hostname sender   --network sig-net -e STUDENT_UID=$STUDENT_UID -v $LAB/sender:/lab   sig-lab:1.0"
h "docker run -dit --name receiver --hostname receiver --network sig-net -e STUDENT_UID=$STUDENT_UID -v $LAB/receiver:/lab sig-lab:1.0"
h "docker ps"

step C7_connectivity
h "docker network inspect sig-net"
c sender "ping -c 3 receiver"
c sender 'echo $STUDENT_UID'
c sender "python3 -c \"import oqs; print(oqs.get_enabled_sig_mechanisms())\""
h "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' sender"
h "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' receiver"

step C8_environment
h 'lscpu | grep -E "Model name|^CPU\(s\)"'
h "free -h | head -2"
h "lsb_release -d 2>/dev/null || grep PRETTY_NAME /etc/os-release; uname -r"
h "docker --version"
h 'docker exec sender pip list 2>/dev/null | grep -iE "cryptography|liboqs"'
h "docker exec sender python3 -c \"import oqs; print(oqs.oqs_version())\""
c sender "grep PRETTY_NAME /etc/os-release; python3 --version"

# environment line used in every graph caption
{
  echo "CPU: $(lscpu | sed -n 's/^Model name:[[:space:]]*//p') ($(nproc) threads), RAM $(free -h | awk '/Mem:/{print $2}')"
  echo "Host: $(. /etc/os-release; echo "$PRETTY_NAME"), kernel $(uname -r), $(docker --version | cut -d, -f1)"
  echo "Container: $(docker exec sender bash -c '. /etc/os-release; echo $PRETTY_NAME'), cryptography $(docker exec sender python3 -c 'import cryptography; print(cryptography.__version__)'), liboqs $(docker exec sender python3 -c 'import oqs; print(oqs.oqs_version())' 2>/dev/null | tail -1)"
} > sender/environment.txt
cp sender/environment.txt receiver/

# ---------------------------------------------------------------- Part D
step D1_alg_names
c sender "python3 -c \"import oqs; print([m for m in oqs.get_enabled_sig_mechanisms() if 'ML-DSA' in m or 'SLH' in m])\""

step D3_keygen
c sender "cd /lab && mkdir -p keys outbox"
for a in ecdsa rsapss mldsa slhdsa; do c sender "python3 keygen.py $a"; done
c sender "ls -l keys outbox"

# ---------------------------------------------------------------- Part E
step E_sign
for a in ecdsa rsapss mldsa slhdsa; do c sender "python3 sign.py $a"; done
c sender "cat outbox/document.txt"
c sender "ls -l outbox"
c sender "sha256sum outbox/document.txt"

# ---------------------------------------------------------------- Part F
step F_transfer
docker exec -d sender bash -c "cd /lab/outbox && exec python3 -u -m http.server 8000 > /lab/http_server.log 2>&1"
sleep 2
c receiver "mkdir -p /lab/inbox && cd /lab/inbox && curl -O http://sender:8000/document.txt"
c receiver 'cd /lab/inbox && for a in ecdsa rsapss mldsa slhdsa; do curl -sO http://sender:8000/${a}.sig; curl -sO http://sender:8000/${a}_public.key; done'
c receiver "ls -l /lab/inbox"
c receiver "sha256sum /lab/inbox/document.txt"
sleep 2
step F_http_server_log
echo "root@sender:/lab# cd /lab/outbox && python3 -m http.server 8000" >> "$LOG"
cat sender/http_server.log >> "$LOG"; cat "$LOG"
docker exec sender pkill -f http.server >/dev/null 2>&1

# ---------------------------------------------------------------- Part G
step G_verify
for a in ecdsa rsapss mldsa slhdsa; do c receiver "cd /lab && python3 verify.py $a"; done
step G_sizes
c sender 'cd /lab && for a in ecdsa rsapss mldsa slhdsa; do echo "$a public=$(stat -c %s outbox/${a}_public.key) private=$(stat -c %s keys/${a}_private.key) sig=$(stat -c %s outbox/${a}.sig) doc=$(stat -c %s outbox/document.txt)"; done'
c receiver 'cd /lab && for a in ecdsa rsapss mldsa slhdsa; do echo "$a received: doc+sig+pk = $(( $(stat -c %s inbox/document.txt) + $(stat -c %s inbox/${a}.sig) + $(stat -c %s inbox/${a}_public.key) )) bytes"; done'

# ---------------------------------------------------------------- Part H
step H_tamper
c receiver "cd /lab && python3 tamper.py doc inbox/document.txt"
for a in ecdsa rsapss mldsa slhdsa; do
  c receiver "cd /lab && python3 verify.py $a inbox/document.txt inbox/${a}_public.key inbox/${a}.sig    # Test 1: original"
done
for a in ecdsa rsapss mldsa slhdsa; do
  c receiver "cd /lab && python3 verify.py $a inbox/document.txt.tampered    # Test 2: modified document"
done
for a in ecdsa rsapss mldsa slhdsa; do
  c receiver "cd /lab && python3 tamper.py sig inbox/${a}.sig"
  c receiver "cd /lab && python3 verify.py $a inbox/document.txt inbox/${a}_public.key inbox/${a}.sig.tampered    # Test 3: modified signature"
done
c receiver "cd /lab && mkdir -p keys outbox"
for a in ecdsa rsapss mldsa slhdsa; do
  # ECDSA: an independent random key - the UID-derived one would equal the sender's key
  opt=""; [ "$a" = ecdsa ] && opt=" --independent"
  c receiver "cd /lab && python3 keygen.py $a$opt    # Test 4: receiver makes ITS OWN key pair"
  c receiver "cd /lab && python3 verify.py $a inbox/document.txt outbox/${a}_public.key inbox/${a}.sig    # Test 4: wrong public key"
done
c receiver "cd /lab && for a in ecdsa rsapss mldsa slhdsa; do cmp -s inbox/\${a}_public.key outbox/\${a}_public.key && echo \"\$a: receiver key IDENTICAL to sender key (not a wrong key!)\" || echo \"\$a: receiver key differs from sender key\"; done"

# ---------------------------------------------------------------- Part I
step I_bench_sender
for r in 1 2 3; do c sender "cd /lab && python3 bench.py results_run$r.csv"; done
step I_bench_receiver
c receiver "cd /lab && python3 bench.py results.csv"
step I_median
# keep the median run (runs ranked by the sum of all mean times) as results.csv
c sender 'cd /lab && for r in 1 2 3; do echo "run $r: sum of mean_ms = $(awk -F, '"'"'NR>1{s+=$5} END{printf \"%.2f\", s}'"'"' results_run$r.csv)"; done'
MED=$(for r in 1 2 3; do echo "$(awk -F, 'NR>1{s+=$5} END{print s}' sender/results_run$r.csv) $r"; done | sort -n | sed -n 2p | cut -d' ' -f2)
c sender "cd /lab && cp results_run$MED.csv results.csv && cat results.csv"

# ---------------------------------------------------------------- Section 15
step S15_plot
c sender "cd /lab && python3 plot.py results.csv outbox/document.txt"
h "docker cp sender:/lab/graphs ./graphs"
h "ls -l graphs"

echo "done - transcripts in $LOGS"
