# Lab 10 (PGP and S/MIME) — run it on your PC

`run_lab10.py` runs **every command of the lab manual** (Parts B and C) in `~/cns-pgp-smime` and
records each command with its real output in `exp10/logs/`. The interactive `gpg --full-generate-key`
questions (key type, size, expiry, name, e-mail, passphrase) are answered automatically, exactly as
the manual says (RSA and RSA, 3072 bits, 1 year, "Alice CNS Lab" / "Bob CNS Lab", the given e-mails).
Tested end to end on Ubuntu 24.04 with GnuPG 2.4.4 and OpenSSL 3.0.13 (the same as WSL Ubuntu 24.04).
It needs almost no disk space (well under 1 MB).

## Steps

```bash
cd ~/sig-lab
git pull
sudo apt install -y gnupg openssl     # usually already installed on Ubuntu
python3 exp10/run_lab10.py
```

- It takes about a minute (most of it is RSA key generation).
- If `~/cns-pgp-smime` already exists, it is **renamed** to `~/cns-pgp-smime.old.<number>`, not deleted.
- It ends with: `done - logs in .../exp10/logs, evidence files in .../exp10/artifacts (no private keys)`

Then push:

```bash
git add exp10
git commit -m "Lab 10 run on my PC"
git push
```

and tell me it's pushed — I'll check the run and build the report.

## If something goes wrong

| Problem | Fix |
|---|---|
| `missing gpg` / `missing openssl` | `sudo apt install -y gnupg openssl` |
| It seems to hang at key generation for more than 2 minutes | Press Ctrl+C, run `gpgconf --kill all`, then run the script again |
| Anything else | Paste me the last ~20 lines of output |
