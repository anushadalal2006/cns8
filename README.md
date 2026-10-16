# CNS Experiment 8: Classical vs Post-Quantum Digital Signatures over Docker

**Name:** Anusha Dalal **UID:** 2024300032

This repository is the `~/sig-lab` folder of the lab sheet. Every part was run for real with `STUDENT_UID=2024300032`.

**To run it on your own PC, follow [RUN_ON_MY_PC.md](RUN_ON_MY_PC.md).**

## What to submit

**The report:** `report/Exp08_Report_2024300032_Anusha_Dalal.docx` (editable) and the matching `.pdf`. It follows the Section 19 order:

| # | Submission item | In the report |
|---|---|---|
| 1 | Hand-drawn digital-signature diagram (Part A) | Section 1: blank page to attach your **handwritten** sheet. Reference to copy from: `report/partA_reference_diagram.png` |
| 2 | Table 1 + screenshots of `docker ps`, `docker network inspect sig-net`, ping test | Section 2: Table 1, Screenshots 1–6 |
| 3 | Screenshots of keygen, signing, transfer (+ sender HTTP log), verification | Section 3: Screenshots 7–12 |
| 4 | Table 2, Table 3 (+ original/modified text), Table 4 | Section 4: Tables 2–4, Screenshots 13–19 |
| 5 | Seven graphs, Tables 5, 6, 7 | Section 5: Graphs 1–7, Screenshot 20, Tables 5–7 |
| 6 | Answers to all discussion questions | Section 6: page to attach your **handwritten** answers (text to copy: `ANSWERS_TO_HANDWRITE.md`) |
| 7 | 200–250 word conclusion | Section 7: page to attach your **handwritten** conclusion (243-word text in `ANSWERS_TO_HANDWRITE.md`) |
| 8 | Source code + Dockerfile | Section 8 (files: `sender/*.py`, `Dockerfile`) |
| 9 | results.csv files (sender, receiver) and UID | Section 9 (files: `results_sender.csv`, `results_receiver.csv`) |

## Layout

```
Dockerfile              exactly the Step C3 Dockerfile
Dockerfile.sandbox      same + proxy CA certificate (only needed on the cloud machine that built the image)
sender/   -> /lab in container "sender"    (programs, outbox/, results*.csv, graphs/, http_server.log)
receiver/ -> /lab in container "receiver"  (programs, inbox/ incl. *.tampered, results.csv)
run_experiment.sh       runs Steps C5 to Section 15 and records every command transcript in logs/
logs/                   raw transcripts (prompt + real output) of every step
screenshots/            terminal screenshots rendered from logs/ (tools/render_screenshots.py)
graphs/                 the seven graphs (copied out with docker cp)
report/                 the lab report (.docx + .pdf), Part A reference diagram
tools/                  screenshot / document / reference-diagram generators
```

Private keys (`keys/`) are deliberately not committed. Their sizes are in Table 2.

## Reproduce

```bash
docker build -t sig-lab:1.0 .
STUDENT_UID=2024300032 ./run_experiment.sh
python3 tools/render_screenshots.py && python3 tools/make_docs.py
```

## Note on Test 4

The ECDSA key is derived from the UID (Section 5), and both containers have the same UID, so running `keygen.py ecdsa` on the receiver would recreate the sender's exact key. That would not be a wrong key at all. For Test 4 the receiver therefore uses `keygen.py ecdsa --independent`, an ECDSA key from the secure random generator. RSA-PSS, ML-DSA and SLH-DSA keys are random anyway. `cmp` in Screenshot 16 confirms all four receiver keys differ from the sender's, and all four verifications FAIL.
