"""Render the Lab 10 command transcripts (exp10/logs/*.log) as terminal screenshots.

Look: Windows Terminal + Ubuntu (Campbell colours, Cascadia Mono), the prompt recorded in the logs,
and bash's "> " prompt on continuation lines of multi-line commands. Output is the real output.
usage: python3 exp10/tools/render_terminal.py   ->  exp10/terminal_screenshots/*.png
"""
import os
import re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
EXP9 = os.path.dirname(HERE)
LOGS = os.path.join(EXP9, "logs")
OUT = os.path.join(EXP9, "terminal_screenshots")
FONT = ImageFont.truetype(os.path.join(os.path.dirname(EXP9), "tools", "fonts", "CascadiaMono-Regular.ttf"), 20)
BG, FG, GREEN, BLUE = "#0C0C0C", "#CCCCCC", "#16C60C", "#3B78FF"
COLS, LINE_H, PAD, MAX_ROWS = 116, 23, 4, 62
CW = FONT.getlength("M")
PROMPT_RE = re.compile(r"^([\w.-]+@[\w.-]+):(~?[\w/.-]*)\$ (.*)$")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def parse(path):
    """-> list of blocks: {"user", "dir", "cmd": [lines], "out": [lines]}"""
    lines = ANSI.sub("", open(path, encoding="utf-8", errors="replace").read()).split("\n")
    blocks, i = [], 0
    while i < len(lines):
        m = PROMPT_RE.match(lines[i])
        if not m:
            if blocks:
                blocks[-1]["out"].append(lines[i])
            i += 1
            continue
        cmd = [m.group(3)]
        i += 1
        heredoc = re.search(r"<<'?(\w+)'?\s*$", cmd[0])
        if heredoc:                                   # cat > file <<'EOF' ... EOF
            while i < len(lines):
                cmd.append(lines[i]); i += 1
                if lines[i - 1] == heredoc.group(1):
                    break
        elif cmd[0].startswith("for ") and "done" not in cmd[0]:
            while i < len(lines):
                cmd.append(lines[i]); i += 1
                if lines[i - 1].strip() == "done":
                    break
        else:
            while cmd[-1].endswith("\\") and i < len(lines):
                cmd.append(lines[i]); i += 1
        blocks.append({"user": m.group(1), "dir": m.group(2), "cmd": cmd, "out": []})
    for b in blocks:
        while b["out"] and not b["out"][-1].strip():
            b["out"].pop()
    return blocks


def rows_of(blocks, final_prompt):
    rows, last = [], None
    for b in blocks:
        last = b
        rows.append([(b["user"], GREEN), (":", FG), (b["dir"], BLUE), ("$ ", FG), (b["cmd"][0], FG)])
        rows.extend([[("> " + c, FG)] for c in b["cmd"][1:]])
        rows.extend([[(o.expandtabs(8), FG)] for o in b["out"]])
    if final_prompt and last:
        rows.append([(last["user"], GREEN), (":", FG), (last["dir"], BLUE), ("$ ", FG), ("\0", FG)])
    out = []                                          # wrap at the terminal width
    for segs in rows:
        line, n = [], 0
        for text, col in segs:
            if text == "\0":
                line.append((text, col)); continue
            while True:
                take = text[:COLS - n]
                line.append((take, col)); n += len(take); text = text[len(take):]
                if not text:
                    break
                out.append(line); line, n = [], 0
        out.append(line)
    return out


def draw(rows, path):
    w = int(PAD * 2 + CW * COLS)
    img = Image.new("RGB", (w, PAD * 2 + LINE_H * len(rows)), BG)
    d = ImageDraw.Draw(img)
    for i, segs in enumerate(rows):
        x, y = PAD, PAD + i * LINE_H
        for text, col in segs:
            if text == "\0":
                d.rectangle([x + 1, y + 2, x + 2, y + LINE_H - 3], fill=FG); continue
            d.text((x, y), text, font=FONT, fill=col)
            x += CW * len(text)
    img.save(path)


def shot(name, log, blocks=None, out_range=None, final_prompt=True):
    """blocks: indices of command blocks to show; out_range: (start, end) slice of one block's
    output (a scrolled view of a long output). Images taller than MAX_ROWS are split."""
    bl = parse(os.path.join(LOGS, log))
    sel = bl if blocks is None else [bl[i] for i in blocks]
    if out_range:
        sel = [dict(sel[0], out=sel[0]["out"][out_range[0]:out_range[1]])]
        if out_range[0] > 0:                          # continuing a scrolled output: no prompt line
            rows = rows_of(sel, final_prompt)[1 + len(sel[0]["cmd"]) - 1:]
            return save_split(name, rows)
    return save_split(name, rows_of(sel, final_prompt))


def save_split(name, rows):
    files = []
    parts = [rows[i:i + MAX_ROWS] for i in range(0, len(rows), MAX_ROWS)] or [rows]
    for k, part in enumerate(parts):
        fname = f"{name}.png" if len(parts) == 1 else f"{name}_{k + 1}.png"
        draw(part, os.path.join(OUT, fname))
        files.append(fname)
    return files


# (file stem, heading, log, blocks, out_range)
SHOTS = [
    ("00_environment", "Table 1 evidence: operating system, kernel, GnuPG and OpenSSL versions, CPU, RAM, date", "00_environment.log", None, None),
    ("B1_gnupg", "Step B1: GnuPG installed - gpg --version", "B1_gnupg.log", None, None),
    ("B2_directories", "Step B2: separate working directories and GnuPG homes for Alice and Bob", "B2_directories.log", None, None),
    ("B3_alice_keygen", "Step B3: Alice's key pair (RSA and RSA, 3072 bits) - gpg --full-generate-key, list-keys, list-secret-keys", "B3_alice_keygen.log", None, None),
    ("B3_bob_keygen", "Step B3: Bob's key pair (RSA and RSA, 3072 bits) and key listing", "B3_bob_keygen.log", None, None),
    ("B4_export_import", "Step B4: export public keys only, import into the other keyring, compare fingerprints", "B4_export_import.log", None, None),
    ("B5_sign", "Step B5: message created and signed by Alice (detached ASCII-armored signature)", "B5_sign.log", None, None),
    ("B6_verify", "Step B6: Bob verifies Alice's detached signature - Good signature (trust warning noted separately)", "B6_verify.log", None, None),
    ("B7_encrypt_decrypt", "Step B7: Alice encrypts for Bob; Bob decrypts with his private key", "B7_encrypt_decrypt.log", None, None),
    ("B7_sign_encrypt", "Step B7: signed-and-encrypted message; Bob decrypts and sees the signature status", "B7_sign_encrypt.log", None, None),
    ("B8_tamper", "Step B8: tampered message checked against the original signature - BAD signature", "B8_tamper.log", None, None),
    ("B9_wrong_private_key", "Table 2 (optional row): decryption with a non-matching private key fails; transfer folder contents", "B9_wrong_private_key.log", None, None),
    ("C1_workspace", "Step C1: OpenSSL version and S/MIME workspace", "C1_workspace.log", None, None),
    ("C2_ca", "Step C2: lab CA certificate (CA:TRUE, keyCertSign, cRLSign)", "C2_ca.log", None, None),
    ("C3_alice_cert", "Step C3: Alice's key, CSR and certificate signed by the lab CA", "C3_alice_cert.log", None, None),
    ("C4_bob_cert", "Step C4: Bob's key, CSR and certificate; subject, issuer and validity of both certificates", "C4_bob_cert.log", None, None),
    ("C4b_alice_cert_text", "Certificate details: openssl x509 -text of Alice's certificate", "C4b_alice_cert_text.log", None, None),
    ("C5_sign", "Step C5: S/MIME signed message (first 15 lines)", "C5_sign.log", None, None),
    ("C6_verify", "Step C6: signed message verified with the lab CA - Verification successful", "C6_verify.log", None, None),
    ("C7_C8_encrypt_decrypt", "Steps C7-C8: encrypted for Bob (enveloped data) and decrypted with bob.key", "C7_C8_encrypt_decrypt.log", None, None),
    ("C9_sign_encrypt", "Step C9: sign then encrypt; Bob decrypts and verifies the recovered signed message", "C9_sign_encrypt.log", None, None),
    ("C10_tamper", "Step C10: one character of the signed body changed - Verification failure (digest failure)", "C10_tamper.log", None, None),
    ("C10_untrusted", "Step C10: wrong CA / no CA file - certificate trust failure; with -noverify the signature itself is valid", "C10_untrusted.log", None, None),
]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    manifest = []
    for stem, heading, log, blocks, rng in SHOTS:
        files = shot(stem, log, blocks, rng)
        manifest.append((heading, files))
        print(stem, "->", ", ".join(files))
    with open(os.path.join(OUT, "manifest.txt"), "w") as f:
        for heading, files in manifest:
            f.write(heading + "\t" + ",".join(files) + "\n")
