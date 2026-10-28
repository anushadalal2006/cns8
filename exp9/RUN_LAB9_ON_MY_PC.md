# Lab 9 (Two-Tier PKI with X.509) — run it on your PC

`run_lab9.sh` runs **every command of the lab manual** (Parts A to G) in `~/pki-lab`, exactly as the
manual writes them, and records each command with its real output in `exp9/logs/`. At the end it
copies the submission files (certificates, CRLs, configs, nginx logs, captures, **no private keys**)
into `exp9/submission/`. I tested it end to end on Ubuntu 24.04 with OpenSSL 3.0.13, nginx 1.24.0,
curl 8.5.0 and tshark 4.2.2 (the same versions as your WSL Ubuntu 24.04).

Everything (serial numbers, dates, fingerprints, capture frames) will come from **your** machine.

## Step 1 — Get the script

```bash
cd ~/sig-lab
git pull
```

## Step 2 — Install the tools (needs your Ubuntu password)

```bash
sudo apt update
sudo apt install -y openssl nginx curl wireshark tshark
```

If a blue screen asks **"Should non-superusers be able to capture packets?"**, choose **No**
(the script uses `sudo` for capturing).

## Step 3 — Run the whole lab (about 1–2 minutes)

Close other programs that might use ports **8443** or **2560**, then:

```bash
cd ~/sig-lab
bash exp9/run_lab9.sh
```

- It asks for your **Ubuntu password once** (for `/etc/hosts` and for capturing on `lo`).
- If you already have a `~/pki-lab` folder, it is **renamed** to `~/pki-lab.old.<number>`, not deleted.
- It ends with: `done - logs in .../exp9/logs, submission files in .../exp9/submission (no private keys)`

Quick check:

```bash
grep -c "verify error\|no required" exp9/submission/nginx/error_log_excerpts.txt   # should print 8
ls exp9/submission/captures                                                       # keys.log tls12.pcapng tls13.pcapng
```

## Step 4 — Wireshark screenshots (Part F, Task 4)

The manual wants screenshots **from Wireshark** with the relevant packets highlighted. The script
already made the captures; you only need to open them and take the screenshots.

**Copy the captures to Windows** (replace `YOURWINDOWSNAME`; `ls /mnt/c/Users` shows it):

```bash
mkdir -p /mnt/c/Users/YOURWINDOWSNAME/Downloads/lab9_captures
cp ~/sig-lab/exp9/submission/captures/* /mnt/c/Users/YOURWINDOWSNAME/Downloads/lab9_captures/
```

Install Wireshark for Windows (wireshark.org) if you don't have it. Then take these screenshots:

| # | Open | Display filter | Click on / expand | Save as |
|---|---|---|---|---|
| 1 | `tls12.pcapng` | `tls.handshake` | the **Client Hello** row → expand *Handshake Protocol* → *Extension: server_name* (SNI) and *Cipher Suites* | `F1_clienthello_tls12.png` |
| 2 | `tls12.pcapng` | `tls.handshake` | the **Server Hello** row → *Cipher Suite* | `F1_serverhello_tls12.png` |
| 3 | `tls12.pcapng` | `tls.handshake.type == 11` | the first row → expand *Certificate* → *signedCertificate* → *issuer*, *validity*, *subject*, *extensions* | `F1_certificate_tls12.png` |
| 4 | `tls12.pcapng` | `tls.handshake` | frame with **Certificate Request**, then the client's frame with **Certificate Verify** | `F1_certreq_certverify_tls12.png` |
| 5 | `tls13.pcapng` | `tls.handshake` | show that after Server Hello everything is **Application Data** | `F2_tls13_encrypted.png` |
| 6 | `tls13.pcapng` | `tls.handshake.type == 11` | (shows **no packets** without the key log) | `F2_tls13_no_certificate.png` |
| 7 | `tls13.pcapng` + key log* | `tls.handshake` | now Certificate / Certificate Verify / Finished are visible | `F3_tls13_decrypted.png` |
| 8 | `tls13.pcapng` + key log* | `tls.handshake.type == 11` | expand the client **Certificate** (CN=alice) | `F3_tls13_certificate.png` |

\*Key log: *Edit → Preferences → Protocols → TLS → (Pre)-Master-Secret log filename* → choose
`keys.log` from the same folder → OK. (For screenshots 5 and 6, clear that field first.)

Use **Win + Shift + S** for screenshots. Save them in `Downloads\lab9_captures\screenshots`, then
copy them into the repo:

```bash
mkdir -p ~/sig-lab/exp9/wireshark_screenshots
cp /mnt/c/Users/YOURWINDOWSNAME/Downloads/lab9_captures/screenshots/*.png ~/sig-lab/exp9/wireshark_screenshots/
```

## Step 5 — Push

```bash
cd ~/sig-lab
git add exp9
git commit -m "Lab 9 run on my PC"
git push
```

Then tell me it's pushed. I'll check the run and build the report (Parts A–G with your outputs,
terminal screenshots, your Wireshark screenshots, answers to all Tasks) and the submission zip.

## If something goes wrong

| Problem | Fix |
|---|---|
| `missing: tshark` (or nginx …) | Do Step 2 |
| `bind() to 0.0.0.0:8443 failed (98: Address in use)` | Another nginx is running: `pkill nginx`, then run the script again |
| `sudo: a password is required` / wrong password | Reset it from PowerShell: `wsl -u root`, then `passwd anudalal25` |
| `curl: (6) Could not resolve host: server.lab.local` | `echo '127.0.0.1 server.lab.local' \| sudo tee -a /etc/hosts`, then rerun (WSL can rewrite `/etc/hosts` after a restart) |
| Anything else | Paste me the last ~20 lines of output |
