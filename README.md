# CNS Experiment 8 — Classical vs Post-Quantum Digital Signatures over Docker

**Name:** Anusha Dalal **UID:** 2024300032

This repository is the `~/sig-lab` folder of the lab sheet. All parts were run for real with `STUDENT_UID=2024300032`.

## What to submit (Section 19 order) → where it is

| # | Submission item | File(s) |
|---|---|---|
| 1 | Hand-drawn digital-signature diagram (Part A) | **Draw it by hand** and attach it at the marked page of the report. A reference to copy from is in `report/partA_reference_diagram.png` |
| 2 | Table 1 + screenshots of `docker ps`, `docker network inspect sig-net`, ping test | Report §2; `screenshots/02_docker_ps.png`, `03_network_inspect_sig_net.png`, `04_ping_test.png` |
| 3 | Screenshots of keygen, signing, transfer (+ sender HTTP log), verification | Report §3; `screenshots/07…12_*.png` |
| 4 | Table 2 (sizes), Table 3 (tampering + original/modified text), Table 4 (timings) | Report §4 |
| 5 | Seven graphs, Tables 5, 6, 7 | `graphs/graph1…7_*.png`; Report §5–6 |
| 6 | Answers to all discussion questions | Report §7 |
| 7 | 200–250 word conclusion (249 words) | Report §8 |
| 8 | Source code + Dockerfile | `sender/{common,keygen,sign,verify,tamper,bench,plot}.py`, `Dockerfile`; also printed in Report §9 |
| 9 | results.csv files (sender, receiver) and UID | `results_sender.csv`, `results_receiver.csv` (also in `sender/`, `receiver/`); Report §10 |

**The report:** `report/CNS_Exp08_Digital_Signatures_2024300032_Anusha_Dalal.docx` (editable, so you can insert the scan of your diagram) and `.pdf`.

## Layout

```
Dockerfile              exactly the Step C3 Dockerfile
Dockerfile.sandbox      same + proxy CA certificate (only needed on the cloud build machine that ran this)
sender/   -> /lab in container "sender"    (programs, outbox/, results*.csv, graphs/, http_server.log)
receiver/ -> /lab in container "receiver"  (programs, inbox/ incl. *.tampered, results.csv, tcpdump.txt)
run_experiment.sh       runs Steps C5–Section 15 end to end and saves every command transcript in logs/
logs/                   raw transcripts (prompt + real output) of every step
screenshots/            terminal screenshots rendered from logs/ (tools/render_screenshots.py)
graphs/                 the seven graphs (copied out with docker cp)
report/                 lab report (.docx/.pdf) + Part A reference diagram
tools/                  report / screenshot / reference-diagram generators
```

Private keys (`keys/`) are deliberately not committed, consistent with "the private key never leaves the sender"; their sizes are in Table 2 and in `logs/D3_keygen.log`.

## Reproduce

```bash
docker build -t sig-lab:1.0 .
STUDENT_UID=2024300032 ./run_experiment.sh
python3 tools/render_screenshots.py && python3 tools/make_report.py
```

## Notable result

In Test 4 (wrong public key), **ECDSA returns PASS**. The ECDSA key is derived from the UID (Section 5), and both containers get the same UID, so the receiver's "own" key is byte-identical to the sender's (`cmp` confirms this). This shows the low-entropy-key weakness from the Section 5 warning. A supplementary Test 4b uses an ECDSA key from a different UID and gives FAIL. RSA-PSS, ML-DSA and SLH-DSA give FAIL in Test 4 as expected.
