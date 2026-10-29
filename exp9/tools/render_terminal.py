"""Render the Lab 9 command transcripts (exp9/logs/*.log) as terminal screenshots.

Look: Windows Terminal + Ubuntu (Campbell colours, Cascadia Mono), the prompt recorded in the logs,
and bash's "> " prompt on continuation lines of multi-line commands. Output is the real output.
usage: python3 exp9/tools/render_terminal.py   ->  exp9/terminal_screenshots/*.png
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
    ("01_setup", "Setup: folder layout, index.txt, serial and crlnumber files", "01_setup.log", None, None),
    ("A1_root_config", "Part A.1: root/openssl.cnf", "A1_root_config.log", None, None),
    ("A2_root_key_cert", "Part A.2: 4096-bit Root key and self-signed Root certificate (10 years)", "A2_root_key_cert.log", None, None),
    ("A3_root_inspect", "Part A.3: openssl x509 -text of the Root certificate", "A3_root_inspect.log", None, None),
    ("B1_intermediate_config", "Part B.1: intermediate/openssl.cnf", "B1_intermediate_config.log", None, None),
    ("B2_intermediate_sign", "Part B.2: Intermediate key and CSR, signed by the Root (openssl ca)", "B2_intermediate_key_csr_sign.log", None, None),
    ("B3_chain_verify", "Part B.3: chain file and verification of the Intermediate against the Root", "B3_chain_verify.log", None, None),
    ("B4_intermediate_inspect", "Part B: openssl x509 -text of the Intermediate certificate", "B4_intermediate_inspect.log", None, None),
    ("B5_task_demos", "Task B: certificate signed by a leaf (Alice) and the pathlen:0 test", "B5_task_demos.log", None, None),
    ("C1_server_cert", "Part C.1: server key, CSR, certificate and full chain", "C1_server_cert.log", None, None),
    ("C2_client_certs", "Part C.2: client certificates for Alice and Bob", "C2_client_certs.log", None, None),
    ("C3_verify", "Part C.3: verification of server and client certificates", "C3_verify.log", None, None),
    ("C4_task", "Task C: index.txt, Alice with -purpose sslserver, EKU and SAN", "C4_task.log", None, None),
    ("C5_server_inspect", "Part C: openssl x509 -text of the server certificate", "C5_server_inspect.log", None, None),
    ("D1_nginx_config", "Part D.1: nginx.conf and starting nginx on port 8443", "D1_nginx_config.log", None, None),
    ("D2_test", "Part D.2: valid client (Alice) and no client certificate (HTTP 400), with error.log", "D2_test.log", None, None),
    ("D3_s_client", "Part D.2: openssl s_client -showcerts (chain and acceptable client CA names)", "D3_s_client.log", None, None),
    ("E1_revoke_crl", "Part E.1: revoke Bob, generate both CRLs and the combined CRL", "E1_revoke_crl.log", None, None),
    ("E1b_verify_crl", "Part E.1: CRL check with OpenSSL (Bob revoked, Alice OK)", "E1b_verify_crl.log", None, None),
    ("E2_nginx_crl", "Part E.2: ssl_crl in nginx: Alice accepted, Bob rejected", "E2_nginx_crl.log", None, None),
    ("E2b_without_root_crl", "Part E.2: without the Root CRL even Alice fails (error 3), then restored", "E2b_without_root_crl.log", None, None),
    ("E3_responder", "Part E.3 (terminal 2): OCSP responder on port 2560", "E3_ocsp_responder.log", None, (0, 22)),
    ("E3_alice_top", "Part E.3: OCSP query for Alice - response data", "E3_ocsp.log", [0], (0, 16)),
    ("E3_alice_end", "Part E.3: OCSP query for Alice - end of output (status good)", "E3_ocsp.log", [0], (166, 176)),
    ("E3_bob_top", "Part E.3: OCSP query for Bob - response data (revoked, keyCompromise)", "E3_ocsp.log", [1], (0, 19)),
    ("E3_bob_end", "Part E.3: OCSP query for Bob - end of output (status revoked)", "E3_ocsp.log", [1], (168, 178)),
    ("E3_aia", "Task E: OCSP URL in the Authority Information Access extension", "E3_ocsp.log", [2], None),
    ("F1_capture12", "Part F.1 (terminal 2): tshark capture on lo, tcp port 8443 (TLS 1.2)", "F1_tls12_tshark_terminal.log", None, None),
    ("F1_tls12", "Part F.1: TLS 1.2 handshake - ClientHello, ServerHello, Certificate, CertificateRequest, CertificateVerify", "F1_tls12.log", None, None),
    ("F2_capture13", "Part F.2 (terminal 2): tshark capture on lo, tcp port 8443 (TLS 1.3)", "F2_tls13_tshark_terminal.log", None, None),
    ("F2_tls13", "Part F.2: TLS 1.3 handshake without the key log - everything after ServerHello is encrypted", "F2_tls13.log", None, None),
    ("F3_tls13_decrypted", "Part F.3: TLS 1.3 handshake decrypted with keys.log", "F3_tls13_decrypted.log", None, None),
    ("G1_expired", "Part G.1: expired client certificate (eve)", "G1_expired.log", None, None),
    ("G2_untrusted", "Part G.2: untrusted self-signed client (mallory)", "G2_untrusted.log", None, None),
    ("G3_wrong_purpose", "Part G.3: wrong purpose (server certificate used as a client certificate)", "G3_wrong_purpose.log", None, None),
    ("G4_hostname", "Part G.4: hostname mismatch (wrong.lab.local)", "G4_hostname.log", None, None),
    ("G5_missing_intermediate", "Part G.5: missing intermediate (leaf only as ssl_certificate), then restored", "G5_missing_intermediate.log", None, None),
    ("G6_revoked", "Part G.6: revoked certificate (Bob)", "G6_revoked.log", None, None),
    ("G7_errorlog", "Part G: all client-certificate errors in nginx error.log", "G7_errorlog_summary.log", None, None),
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
