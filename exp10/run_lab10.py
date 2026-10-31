#!/usr/bin/env python3
"""run_lab10.py - CNS Lab: Secure e-mail using PGP (GnuPG) and S/MIME (OpenSSL).

Runs every command of the lab manual (Parts B and C) in ~/cns-pgp-smime and records each command
with its real terminal output in exp10/logs/. Commands run inside a pseudo-terminal, and the
interactive prompts of `gpg --full-generate-key` (key type, size, expiry, name, e-mail, passphrase)
are answered exactly as a person would type them, so the transcript is the real interactive session.
Evidence files (public keys, messages, signatures, encrypted files, certificates; NO private keys)
are copied to exp10/artifacts/.

usage (Ubuntu / WSL):   python3 exp10/run_lab10.py
"""
import os
import pty
import pwd
import re
import select
import shutil
import socket
import subprocess
import sys
import time

NAME, UID = "Anusha Dalal", "2024300032"
HOME = os.path.expanduser("~")
LAB = os.path.join(HOME, "cns-pgp-smime")
HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, "logs")
ART = os.path.join(HERE, "artifacts")
USER_HOST = f"{pwd.getpwuid(os.getuid()).pw_name}@{socket.gethostname()}"
PASS = {"alice": "Alice-CNS-lab-pass", "bob": "Bob-CNS-lab-pass"}   # test passphrases (lab only)
ANSI = re.compile(rb"\x1b\[\?2004[hl]")                            # bracketed-paste mode markers

env = dict(os.environ)
env.pop("GNUPGHOME", None)
cwd = HOME
LOG = None


def tilde(path):
    return "~" + path[len(HOME):] if path.startswith(HOME) else path


def step(name):
    global LOG
    LOG = open(os.path.join(LOGS, name + ".log"), "w")
    print(f"=== {name} ===", flush=True)
    run(f'echo "Name: {NAME} | UID: {UID}"')


def drive(cmd, responders, timeout=120):
    """run cmd in a pty; responders = [(regex, answer, once)] answered when the prompt appears"""
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        os.execvpe("bash", ["bash", "-c", cmd], env)
    out, used, last = b"", set(), time.time()
    while True:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            out += data
            last = time.time()
            tail = ANSI.sub(b"", out).decode(errors="replace")[-400:]
            for i, (rx, ans, once) in enumerate(responders):
                if once and i in used:
                    continue
                if re.search(rx + r"\s*$", tail):
                    used.add(i)
                    time.sleep(0.1)
                    os.write(fd, (ans + "\n").encode())
                    break
        elif time.time() - last > timeout:
            os.kill(pid, 9)
            break
    _, status = os.waitpid(pid, 0)
    text = ANSI.sub(b"", out).decode(errors="replace").replace("\r\n", "\n").replace("\r", "")
    return text, os.waitstatus_to_exitcode(status)


def run(cmd, responders=()):
    """log 'prompt + command', run it (pty), log its output; handle export/cd like a shell would"""
    global cwd
    LOG.write(f"{USER_HOST}:{tilde(cwd)}$ {cmd}\n")
    m = re.fullmatch(r"export (\w+)=(.+)", cmd)
    if m:
        env[m.group(1)] = os.path.expandvars(m.group(2).replace("$HOME", HOME))
        LOG.write("\n"); LOG.flush()
        return ""
    m = re.fullmatch(r"cd (\S+)", cmd)
    if m:
        cwd = os.path.expanduser(m.group(1))
        LOG.write("\n"); LOG.flush()
        return ""
    who = "alice" if "alice/gnupg" in env.get("GNUPGHOME", "") else "bob"
    resp = list(responders) + [(r"Enter passphrase:", PASS[who], False),
                               (r"Use this key anyway\? \(y/N\)", "y", False)]
    text, code = drive(cmd, resp)
    LOG.write(text.rstrip("\n") + ("\n" if text.strip() else "") + "\n")
    LOG.flush()
    print(text, end="", flush=True)
    return text


def keygen(who, real_name, email):
    run("gpg --full-generate-key", [
        (r"Your selection\?", "1", True),
        (r"What keysize do you want\? \(3072\)", "3072", True),
        (r"Key is valid for\? \(0\)", "1y", True),
        (r"Is this correct\? \(y/N\)", "y", True),
        (r"Real name:", real_name, True),
        (r"Email address:", email, True),
        (r"Comment:", "", True),
        (r"\(O\)kay/\(Q\)uit\?", "O", True),
    ])


def main():
    for t in ("gpg", "openssl"):
        if not shutil.which(t):
            sys.exit(f"missing {t}: sudo apt install -y gnupg openssl")
    os.makedirs(LOGS, exist_ok=True)
    for f in os.listdir(LOGS):
        os.remove(os.path.join(LOGS, f))
    if os.path.exists(LAB):
        os.rename(LAB, f"{LAB}.old.{int(time.time())}")
    global cwd

    # ------------------------------------------------------------ Table 1: environment
    step("00_environment")
    run("lsb_release -d 2>/dev/null || grep PRETTY_NAME /etc/os-release")
    run("uname -r")
    run("gpg --version | head -3")
    run("openssl version")
    run("lscpu | grep -E 'Model name|^CPU\\(s\\)'")
    run("free -h | head -2")
    run("date")

    # ------------------------------------------------------------ Part B: PGP / OpenPGP
    step("B1_gnupg")
    run("gpg --version")

    step("B2_directories")
    run("mkdir -p ~/cns-pgp-smime/{alice,bob,transfer}")
    run("cd ~/cns-pgp-smime")
    run("mkdir -p ~/cns-pgp-smime/alice/gnupg ~/cns-pgp-smime/bob/gnupg")
    run("chmod 700 ~/cns-pgp-smime/alice/gnupg ~/cns-pgp-smime/bob/gnupg")
    # deviation (terminal without a graphical pinentry): ask for passphrases in the terminal
    run('echo "pinentry-mode loopback" > ~/cns-pgp-smime/alice/gnupg/gpg.conf')
    run('echo "pinentry-mode loopback" > ~/cns-pgp-smime/bob/gnupg/gpg.conf')
    run("ls -la ~/cns-pgp-smime ~/cns-pgp-smime/alice ~/cns-pgp-smime/bob")

    step("B3_alice_keygen")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/alice/gnupg")
    keygen("alice", "Alice CNS Lab", "alice-lab@example.test")
    run("gpg --list-keys")
    run("gpg --list-secret-keys")

    step("B3_bob_keygen")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/bob/gnupg")
    keygen("bob", "Bob CNS Lab", "bob-lab@example.test")
    run("gpg --list-keys")

    step("B4_export_import")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/alice/gnupg")
    run("gpg --armor --export alice-lab@example.test > ~/cns-pgp-smime/alice_public.asc")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/bob/gnupg")
    run("gpg --armor --export bob-lab@example.test > ~/cns-pgp-smime/bob_public.asc")
    run("ls -l ~/cns-pgp-smime/*.asc")
    run("head -n 4 ~/cns-pgp-smime/alice_public.asc")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/alice/gnupg")
    run("gpg --import ~/cns-pgp-smime/bob_public.asc")
    run("gpg --fingerprint bob-lab@example.test")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/bob/gnupg")
    run("gpg --import ~/cns-pgp-smime/alice_public.asc")
    run("gpg --fingerprint alice-lab@example.test")

    step("B5_sign")
    run("printf 'CNS Lab: PGP secure e-mail test. Message ID: CNS-PGP-01.\\n' > ~/cns-pgp-smime/message.txt")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/alice/gnupg")
    run("gpg --armor --local-user alice-lab@example.test --detach-sign --output ~/cns-pgp-smime/message.txt.asc ~/cns-pgp-smime/message.txt")
    run("cp ~/cns-pgp-smime/message.txt* ~/cns-pgp-smime/transfer/")
    run("cat ~/cns-pgp-smime/transfer/message.txt ~/cns-pgp-smime/transfer/message.txt.asc")

    step("B6_verify")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/bob/gnupg")
    run("gpg --verify ~/cns-pgp-smime/transfer/message.txt.asc ~/cns-pgp-smime/transfer/message.txt")

    step("B7_encrypt_decrypt")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/alice/gnupg")
    run("gpg --armor --encrypt --recipient bob-lab@example.test --output ~/cns-pgp-smime/transfer/message.txt.pgp ~/cns-pgp-smime/message.txt")
    run("head -n 6 ~/cns-pgp-smime/transfer/message.txt.pgp")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/bob/gnupg")
    run("gpg --output ~/cns-pgp-smime/decrypted_message.txt --decrypt ~/cns-pgp-smime/transfer/message.txt.pgp")
    run("cat ~/cns-pgp-smime/decrypted_message.txt")

    step("B7_sign_encrypt")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/alice/gnupg")
    run("gpg --armor --sign --encrypt --local-user alice-lab@example.test --recipient bob-lab@example.test --output ~/cns-pgp-smime/transfer/signed_encrypted.pgp ~/cns-pgp-smime/message.txt")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/bob/gnupg")
    run("gpg --output ~/cns-pgp-smime/decrypted_signed.txt --decrypt ~/cns-pgp-smime/transfer/signed_encrypted.pgp")
    run("cat ~/cns-pgp-smime/decrypted_signed.txt")

    step("B8_tamper")
    run("cp ~/cns-pgp-smime/message.txt ~/cns-pgp-smime/tampered.txt")
    run("printf 'ALTERED' >> ~/cns-pgp-smime/tampered.txt")
    run("cat ~/cns-pgp-smime/tampered.txt; echo")
    run("export GNUPGHOME=$HOME/cns-pgp-smime/bob/gnupg")
    run("gpg --verify ~/cns-pgp-smime/transfer/message.txt.asc ~/cns-pgp-smime/tampered.txt")

    step("B9_wrong_private_key")       # Table 2, optional row
    run("export GNUPGHOME=$HOME/cns-pgp-smime/alice/gnupg")
    run("gpg --output ~/cns-pgp-smime/alice_attempt.txt --decrypt ~/cns-pgp-smime/transfer/message.txt.pgp")
    run("ls -l ~/cns-pgp-smime/transfer")

    # ------------------------------------------------------------ Part C: S/MIME with OpenSSL
    step("C1_workspace")
    run("openssl version")
    run("mkdir -p ~/cns-pgp-smime/smime")
    run("cd ~/cns-pgp-smime/smime")

    step("C2_ca")
    run("openssl req -x509 -newkey rsa:3072 -keyout ca.key -out ca.crt -sha256 -days 365 -nodes -subj '/CN=CNS Lab CA' -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign'")
    run("openssl x509 -in ca.crt -noout -subject -issuer -dates -ext basicConstraints,keyUsage")

    step("C3_alice_cert")
    run("openssl req -newkey rsa:2048 -keyout alice.key -out alice.csr -nodes -subj '/CN=Alice CNS Lab/emailAddress=alice-lab@example.test' -addext 'keyUsage=digitalSignature,keyEncipherment' -addext 'extendedKeyUsage=emailProtection'")
    run("openssl x509 -req -in alice.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out alice.crt -days 180 -sha256")

    step("C4_bob_cert")
    run("openssl req -newkey rsa:2048 -keyout bob.key -out bob.csr -nodes -subj '/CN=Bob CNS Lab/emailAddress=bob-lab@example.test' -addext 'keyUsage=digitalSignature,keyEncipherment' -addext 'extendedKeyUsage=emailProtection'")
    run("openssl x509 -req -in bob.csr -CA ca.crt -CAkey ca.key -CAserial ca.srl -out bob.crt -days 180 -sha256")
    run("openssl x509 -in alice.crt -noout -subject -issuer -dates")
    run("openssl x509 -in bob.crt -noout -subject -issuer -dates")

    step("C4b_alice_cert_text")
    run("openssl x509 -in alice.crt -noout -text")

    step("C5_sign")
    run("printf 'CNS Lab: S/MIME secure e-mail test. Message ID: CNS-SMIME-01.\\n' > message.txt")
    run("openssl smime -sign -in message.txt -text -signer alice.crt -inkey alice.key -out signed.eml")
    run("head -n 15 signed.eml")

    step("C6_verify")
    run("openssl smime -verify -in signed.eml -CAfile ca.crt -out verified_message.txt")
    run("cat verified_message.txt")

    step("C7_C8_encrypt_decrypt")
    run("openssl smime -encrypt -in message.txt -text -out encrypted.eml bob.crt")
    run("head -n 12 encrypted.eml")
    run("openssl smime -decrypt -in encrypted.eml -recip bob.crt -inkey bob.key -out smime_decrypted.txt")
    run("cat smime_decrypted.txt")
    run("diff -u message.txt smime_decrypted.txt")
    # the first two lines are the MIME header added by -text, and MIME uses CRLF line endings;
    # compare the message body itself
    run("tail -n +3 smime_decrypted.txt | tr -d '\\r' | diff - message.txt && echo 'message body is identical to message.txt'")

    step("C9_sign_encrypt")
    run("openssl smime -sign -in message.txt -text -signer alice.crt -inkey alice.key -out signed_for_encryption.eml")
    run("openssl smime -encrypt -in signed_for_encryption.eml -out signed_encrypted.eml bob.crt")
    run("head -n 8 signed_encrypted.eml")
    run("openssl smime -decrypt -in signed_encrypted.eml -recip bob.crt -inkey bob.key -out recovered_signed.eml")
    run("openssl smime -verify -in recovered_signed.eml -CAfile ca.crt -out recovered_original.txt")
    run("tail -n +3 recovered_original.txt | tr -d '\\r' | diff - message.txt && echo 'message body is identical to message.txt'")

    step("C10_tamper")
    run("cp signed.eml signed_tampered.eml")
    # the manual edits one character of the body in a text editor; the same edit with sed:
    run("sed -i 's/S\\/MIME secure e-mail test/S\\/MIME secure e-mail tost/' signed_tampered.eml")
    run("diff signed.eml signed_tampered.eml")
    run("openssl smime -verify -in signed_tampered.eml -CAfile ca.crt -out tampered_output.txt")

    step("C10_untrusted")
    run("openssl req -x509 -newkey rsa:2048 -keyout other_ca.key -out other_ca.crt -nodes -days 30 -subj '/CN=Some Other CA'")
    run("openssl smime -verify -in signed.eml -CAfile other_ca.crt -out untrusted_output.txt")
    run("openssl smime -verify -in signed.eml -out no_cafile_output.txt")
    run("openssl smime -verify -in signed.eml -noverify -out noverify_output.txt")
    run("ls -l ~/cns-pgp-smime/smime")

    # ------------------------------------------------------------ evidence files (no private keys)
    if os.path.exists(ART):
        shutil.rmtree(ART)
    os.makedirs(os.path.join(ART, "pgp"))
    os.makedirs(os.path.join(ART, "smime"))
    for f in ("alice_public.asc", "bob_public.asc", "message.txt", "tampered.txt",
              "decrypted_message.txt", "decrypted_signed.txt"):
        shutil.copy(os.path.join(LAB, f), os.path.join(ART, "pgp", f))
    shutil.copytree(os.path.join(LAB, "transfer"), os.path.join(ART, "pgp", "transfer"))
    for f in sorted(os.listdir(os.path.join(LAB, "smime"))):
        if not f.endswith(".key"):
            shutil.copy(os.path.join(LAB, "smime", f), os.path.join(ART, "smime", f))
    for dp, _, fs in os.walk(ART):
        for f in fs:
            if f.endswith(".key") or "secring" in f or "private-keys" in dp:
                sys.exit(f"private key material found in artifacts: {f}")
    print(f"\ndone - logs in {LOGS}, evidence files in {ART} (no private keys)")


if __name__ == "__main__":
    main()
