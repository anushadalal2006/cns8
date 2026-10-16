# Running Experiment 8 on your own PC (Ubuntu / WSL)

Type every command in your **Ubuntu terminal**. Total time is about 25–40 minutes, most of it the one-time image build.

## Step 1: Move your old folder aside

The lab sheet uses `~/sig-lab`. Keep your old attempt as a backup and use a fresh `~/sig-lab` for this run:

```bash
mv ~/sig-lab ~/sig-lab-old
```

## Step 2: Download the repository into `~/sig-lab`

```bash
git clone -b claude/gifted-maxwell-44sk0b https://github.com/anushadalal2006/cns8.git ~/sig-lab
cd ~/sig-lab
chmod +x run_experiment.sh
```

If `git clone` asks for a password, the repo is private. Use a GitHub personal access token as the password, or download the branch as a ZIP from GitHub and unzip it so its contents sit directly in `~/sig-lab`.

## Step 3: Remove the old containers and network

The run script recreates them. **This deletes the old `sender` and `receiver` containers**, so copy anything you still need out of them first.

```bash
docker rm -f sender receiver
docker network rm sig-net
docker ps -a          # sender / receiver should no longer be listed
```

(An error like "No such container" is fine: it just means nothing was there.)

## Step 4: Build the image from the lab's Dockerfile (Step C4)

```bash
cd ~/sig-lab
docker build -t sig-lab:1.0 .
docker images         # sig-lab 1.0 should be listed
```

This takes 5–15 minutes because liboqs is compiled. It replaces your old `sig-lab:1.0` image, so the containers now run Ubuntu 24.04 as the lab sheet requires.

If it fails, retry with `docker build --no-cache -t sig-lab:1.0 .`.

## Step 5: Run the whole experiment

```bash
cd ~/sig-lab
STUDENT_UID=2024300032 ./run_experiment.sh
```

It prints `=== C5_network ===`, `=== C6_containers ===` and so on, and ends with `done - transcripts in .../logs`. It takes about 5–10 minutes; SLH-DSA signing is slow, which is expected. **Don't run other heavy programs while it runs**, because that affects the timings.

Quick check that it worked:

```bash
cat sender/environment.txt     # should show YOUR CPU / RAM / kernel
ls graphs                      # 7 graph PNGs
grep RESULT logs/H_tamper.log  # 4 PASS, then 12 FAIL
```

## Step 6: Send the results back

**Option A (easiest): push to GitHub, and I'll regenerate the report for you.**

```bash
cd ~/sig-lab
git add -A
git commit -m "Run on my PC"
git push
```

Then tell me it's pushed. I'll regenerate the screenshots, all tables and graphs, the report (.docx + .pdf) and the numbers in `ANSWERS_TO_HANDWRITE.md`.

If `git push` asks for a password, use a GitHub personal access token (GitHub → Settings → Developer settings → Personal access tokens), not your account password.

**Option B: generate the report yourself.**

```bash
cd ~/sig-lab
sudo apt install -y python3-venv libreoffice-writer       # LibreOffice is only needed for the PDF
python3 -m venv ~/exp8-venv && source ~/exp8-venv/bin/activate
pip install python-docx pillow matplotlib pandas
python3 tools/render_screenshots.py
python3 tools/make_docs.py
```

The report appears in `report/`. Without LibreOffice you still get the .docx; open it in Word and use *Save As → PDF*. With Option B, the numbers in `ANSWERS_TO_HANDWRITE.md` still come from the old run, so ask me to update them.

## If something goes wrong

| Problem | Fix |
|---|---|
| `permission denied` on the Docker socket | `sudo usermod -aG docker $USER`, then close and reopen the terminal |
| `Cannot connect to the Docker daemon` | Start Docker Desktop (WSL) or run `sudo service docker start` |
| `Build the image first` | Do Step 4 |
| `Permission denied` when editing or deleting files in `sender/` or `receiver/` | `sudo chown -R $USER:$USER ~/sig-lab` |
| Anything else | Paste me the last ~20 lines of output |
