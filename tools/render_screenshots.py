"""Render the command transcripts in logs/ as terminal-style PNG screenshots (screenshots/).

Each transcript is a sequence of command blocks; a block starts with a prompt line
("anusha@host:~/sig-lab$ ..." or "root@<container>:/lab# ...") followed by its real output.
usage: python3 tools/render_screenshots.py
"""
import os
import re

from PIL import Image, ImageDraw, ImageFont

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
BOLD = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 15)
PROMPT = re.compile(r"^(anusha@host:~/sig-lab\$|root@\w+:/lab[/\w]*#) ")
MAXW = 150                     # characters per line before wrapping
LINE_H, PAD, BAR = 20, 16, 34


def blocks(path):
    out, cur = [], None
    for line in open(path, encoding="utf-8", errors="replace").read().splitlines():
        if PROMPT.match(line):
            cur = [line]
            out.append(cur)
        elif cur is not None:
            cur.append(line)
    return out


def wrap(line):
    if len(line) > 600:        # e.g. the full list of liboqs mechanisms
        line = line[:590] + " ... (truncated)"
    return [line[i:i + MAXW] for i in range(0, max(len(line), 1), MAXW)] or [""]


def render(title, lines, out):
    rows = [r for l in lines for r in wrap(l)]
    while rows and not rows[-1].strip():
        rows.pop()
    width = max(900, PAD * 2 + int(FONT.getlength("M") * min(MAXW, max(len(r) for r in rows))))
    height = BAR + PAD * 2 + LINE_H * len(rows)
    img = Image.new("RGB", (width, height), "#1e1e1e")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, BAR], fill="#3c3c3c")
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        d.ellipse([12 + i * 22, 11, 26 + i * 22, 25], fill=c)
    d.text((90, 8), title, font=BOLD, fill="#dddddd")
    y = BAR + PAD
    for r in rows:
        m = PROMPT.match(r)
        if m:
            d.text((PAD, y), m.group(1), font=BOLD, fill="#4ec94e" if "anusha" in r else "#ff6b6b")
            d.text((PAD + FONT.getlength(m.group(1) + " "), y), r[m.end():], font=FONT, fill="#ffffff")
        else:
            color = "#d4d4d4"
            if "PASS" in r:
                color = "#4ec94e"
            elif "FAIL" in r:
                color = "#ff6b6b"
            d.text((PAD, y), r, font=FONT, fill=color)
        y += LINE_H
    img.save(out)
    print("wrote", out)


# (output name, window title, log file, block indices or None for all)
SHOTS = [
    ("01_docker_network_create.png", "host: Step C5 - create sig-net", "C5_network.log", None),
    ("02_docker_ps.png", "host: Step C6 - start containers / docker ps", "C6_containers.log", None),
    ("03_network_inspect_sig_net.png", "host: Step C7 - docker network inspect sig-net", "C7_connectivity.log", [0]),
    ("04_ping_test.png", "sender: Step C7 - ping receiver, UID, liboqs, IP addresses", "C7_connectivity.log", [1, 2, 3, 4, 5]),
    ("05_environment.png", "host: Step C8 - execution environment", "C8_environment.log", None),
    ("06_alg_names.png", "sender: Step D1 - algorithm names in liboqs", "D1_alg_names.log", None),
    ("07_keygen.png", "sender: Step D3 - key generation (all four)", "D3_keygen.log", None),
    ("08_signing.png", "sender: Part E - signing (all four)", "E_sign.log", None),
    ("09_transfer_receiver.png", "receiver: Part F - download over sig-net", "F_transfer.log", None),
    ("10_transfer_sender_http_log.png", "sender: Part F - HTTP server log", "F_http_server_log.log", None),
    ("11_tcpdump.png", "receiver: Part F (optional) - tcpdump port 8000", "F_tcpdump.log", None),
    ("12_verification.png", "receiver: Part G - verification (all four)", "G_verify.log", None),
    ("13_sizes.png", "Part G - file sizes (stat -c %s)", "G_sizes.log", None),
    ("14_tamper_test1_test2.png", "receiver: Part H - Tests 1 and 2", "H_tamper.log", list(range(0, 9))),
    ("15_tamper_test3.png", "receiver: Part H - Test 3 (one bit of signature)", "H_tamper.log", list(range(9, 17))),
    ("16_tamper_test4.png", "receiver: Part H - Test 4 (wrong public key) + 4b", "H_tamper.log", list(range(17, 29))),
    ("17_bench_sender.png", "sender: Part I - bench.py (3 runs)", "I_bench_sender.log", None),
    ("18_bench_receiver.png", "receiver: Part I - bench.py", "I_bench_receiver.log", None),
    ("19_bench_sender_cpus1.png", "sender: Part I (optional) - --cpus 1 + median run", "I_bench_sender_cpus1.log", None),
    ("20_plot.png", "Section 15 - plot.py + docker cp", "S15_plot.log", None),
]

if __name__ == "__main__":
    os.makedirs("screenshots", exist_ok=True)
    for name, title, log, idx in SHOTS:
        bl = blocks(os.path.join("logs", log))
        sel = bl if idx is None else [bl[i] for i in idx if i < len(bl)]
        lines = [l for b in sel for l in b + [""]]
        render(title, lines, os.path.join("screenshots", name))
