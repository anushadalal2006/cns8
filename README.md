# CNS Experiment 8: Classical vs Post-Quantum Digital Signatures over Docker

**Name:** Anusha Dalal **UID:** 2024300032

This repository is the `~/sig-lab` folder of the lab sheet. Every part was run for real with `STUDENT_UID=2024300032`.

## What to submit (Section 19 order) and where it is

| # | Submission item | File(s) |
|---|---|---|
| 1 | Hand-drawn digital-signature diagram (Part A) | **Draw by hand.** Reference to copy from: `report/partA_reference_diagram.png` |
| 2 | Table 1 + screenshots of `docker ps`, `docker network inspect sig-net`, ping test | Table 1: `report/Exp08_Tables_and_Graphs_2024300032.docx`; Screenshots 3–5: `report/Exp08_Screenshots_2024300032.docx` |
| 3 | Screenshots of keygen, signing, transfer (+ sender HTTP log), verification | Screenshots 8–12: `report/Exp08_Screenshots_2024300032.docx` |
| 4 | Table 2, Table 3 (+ original/modified text), Table 4 | `report/Exp08_Tables_and_Graphs_2024300032.docx` |
| 5 | Seven graphs, Tables 5, 6, 7 | `report/Exp08_Tables_and_Graphs_2024300032.docx` (PNG files in `graphs/`) |
| 6 | Answers to all discussion questions | **Handwritten.** Text to copy: `ANSWERS_TO_HANDWRITE.md` |
| 7 | 200–250 word conclusion | **Handwritten.** Text to copy (249 words): `ANSWERS_TO_HANDWRITE.md` |
| 8 | Source code + Dockerfile | `sender/common.py keygen.py sign.py verify.py tamper.py bench.py plot.py`, `Dockerfile` |
| 9 | results.csv files (sender, receiver) and UID | `results_sender.csv`, `results_receiver.csv` (also `sender/results.csv`, `receiver/results.csv`, `sender/results_run1-3.csv`) |

Both Word documents are editable, and each has a matching PDF in `report/`.

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
report/                 the two Word documents + PDFs, Part A reference diagram
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

In Test 4 (wrong public key), **ECDSA gives PASS**. The ECDSA key is derived from the UID (Section 5) and both containers have the same UID, so the receiver's "own" key is identical to the sender's (`cmp` in Screenshot 16 confirms this). RSA-PSS, ML-DSA and SLH-DSA give FAIL as expected.
