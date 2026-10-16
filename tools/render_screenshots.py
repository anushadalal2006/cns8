"""Render the command transcripts in logs/ as terminal screenshots (screenshots/).

Look: Windows Terminal running Ubuntu (WSL) - Campbell colour scheme, Cascadia Mono,
prompt "<user>@<host>:<dir>$" (as recorded by run_experiment.sh) on the host and "root@<container>:<cwd>#" inside a
container opened with "docker exec -it <container> bash". Each transcript is a sequence of
command blocks (prompt line + its real output) recorded by run_experiment.sh.
usage: python3 tools/render_screenshots.py
"""
import os
import re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = ImageFont.truetype(os.path.join(HERE, "fonts", "CascadiaMono-Regular.ttf"), 20)
BG, FG = "#0C0C0C", "#CCCCCC"
GREEN, BLUE = "#16C60C", "#3B78FF"        # bright green / bright blue (bold PS1 colours)
USER_HOST, HOST_DIR = "user@host", "~"      # replaced by the prompt recorded in the logs
COLS, LINE_H, PAD_X, PAD_Y = 116, 23, 4, 4
CHAR_W = FONT.getlength("M")

HOST_RE = re.compile(r"^([\w.-]+@[\w.-]+):(~?[\w/.-]*)\$ (.*)$")
CTR_RE = re.compile(r"^root@(\w+):(/[\w/]*)# (.*)$")
CD_PREFIX = re.compile(r"^cd (\S+) && (.*)$")


def parse(path):
    """-> list of (context, cwd, command, output_lines); context 'host' or a container name."""
    global USER_HOST, HOST_DIR
    blocks = []
    for line in open(path, encoding="utf-8", errors="replace", newline="").read().split("\n"):
        m, n = HOST_RE.match(line), CTR_RE.match(line)
        if m:
            USER_HOST, HOST_DIR = m.group(1), m.group(2)
            blocks.append(["host", HOST_DIR, m.group(3), []])
        elif n:
            blocks.append([n.group(1), n.group(2), n.group(3), []])
        elif blocks:
            blocks[-1][3].append(line)
    for b in blocks:                      # drop the blank separator lines added by the recorder
        while b[3] and not b[3][-1].strip():
            b[3].pop()
    return blocks


def carriage(line):
    """Emulate \\r: later segments overwrite the start of the line (curl progress meter)."""
    out = ""
    for seg in line.split("\r"):
        out = seg + out[len(seg):]
    return out


def to_rows(blocks, final_prompt=True):
    """Turn blocks into terminal rows: [(segments)], segment = (text, colour)."""
    rows, ctx, cwd = [], None, {}

    def prompt(c):
        if c == "host":
            return [(USER_HOST, GREEN), (":", FG), (HOST_DIR, BLUE), ("$ ", FG)]
        return [(f"root@{c}:{cwd.get(c, '/lab')}# ", FG)]

    def cmd(c, text):
        rows.append(prompt(c) + [(text, FG)])
        for m in re.finditer(r"(?:^|&& )cd (\S+)", text):
            cwd[c] = m.group(1)

    def switch(new):
        nonlocal ctx
        if new == ctx:
            return
        if ctx not in (None, "host"):                 # leave the container shell
            cmd(ctx, "exit")
            rows.append([("exit", FG)])
        if new != "host":                             # open a shell in the container
            cmd("host", f"docker exec -it {new} bash")
            cwd[new] = "/lab"
        ctx = new

    for c, recorded_cwd, command, output in blocks:
        switch(c)
        if c != "host":
            m = CD_PREFIX.match(command)
            if m:                                     # "cd X && cmd": be in X, then run cmd
                if cwd.get(c, "/lab") != m.group(1):
                    cmd(c, f"cd {m.group(1)}")
                command = m.group(2)
        cmd(c, command)
        rows.extend([[(carriage(l), FG)] for l in output])
    if final_prompt and ctx:
        rows.append(prompt(ctx) + [("\0cursor", FG)])
    return rows


def wrap(rows):
    out = []
    for segs in rows:
        line, cur = [], 0
        for text, col in segs:
            if text == "\0cursor":
                line.append((text, col))
                continue
            while text:
                take = text[:COLS - cur]
                line.append((take, col))
                cur += len(take)
                text = text[len(take):]
                if cur >= COLS and text:
                    out.append(line)
                    line, cur = [], 0
        out.append(line)
    return out


def render(blocks, out, final_prompt=True):
    rows = wrap(to_rows(blocks, final_prompt))
    width = int(PAD_X * 2 + CHAR_W * COLS)
    height = PAD_Y * 2 + LINE_H * len(rows)
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    for i, segs in enumerate(rows):
        x, y = PAD_X, PAD_Y + i * LINE_H
        for text, col in segs:
            if text == "\0cursor":
                d.rectangle([x + 1, y + 2, x + 2, y + LINE_H - 3], fill=FG)
                continue
            d.text((x, y), text, font=FONT, fill=col)
            x += CHAR_W * len(text)
    img.save(out)
    print("wrote", out)


# Screenshots in order of execution: (file, heading, log, block indices or None, final prompt)
SHOTS = [
    ("01_docker_images.png", "Step C4: the image sig-lab:1.0 has been built and is listed by docker images",
     "C4_image.log", None, True),
    ("02_network_create.png", "Step C5: user-defined bridge network sig-net created and listed (no containers attached yet)",
     "C5_network.log", None, True),
    ("03_docker_ps.png", "Step C6: sender and receiver containers started on sig-net with STUDENT_UID; docker ps shows both Up",
     "C6_containers.log", None, True),
    ("04_network_inspect.png", "Step C7: docker network inspect sig-net now lists both containers with their IP addresses",
     "C7_connectivity.log", [0], True),
    ("05_ping_test.png", "Step C7: ping by name from sender to receiver, STUDENT_UID inside the container, liboqs mechanisms and container IPs",
     "C7_connectivity.log", [1, 2, 3, 4, 5], True),
    ("06_environment.png", "Step C8: execution environment (CPU, RAM, OS, Docker, cryptography and liboqs versions) for Table 1",
     "C8_environment.log", None, True),
    ("07_alg_names.png", "Step D1: exact ML-DSA / SLH-DSA names in liboqs (ML-DSA-44, SLH_DSA_PURE_SHA2_128S)",
     "D1_alg_names.log", None, True),
    ("08_keygen.png", "Step D3: keygen.py generates the ECDSA, RSA-PSS, ML-DSA and SLH-DSA key pairs and prints their sizes",
     "D3_keygen.log", None, True),
    ("09_signing.png", "Part E: sign.py creates the UID document and signs it with all four algorithms; document SHA-256 noted",
     "E_sign.log", None, True),
    ("10_transfer_receiver.png", "Part F: receiver downloads document, signatures and public keys from http://sender:8000; SHA-256 matches",
     "F_transfer.log", None, True),
    ("11_http_server_log.png", "Part F: sender's HTTP server log showing every request coming from the receiver's IP (172.18.0.3)",
     "F_http_server_log.log", None, False),
    ("12_verification.png", "Part G: verify.py on the receiver prints PASS for all four algorithms",
     "G_verify.log", None, True),
    ("13_sizes.png", "Part G: key, signature and document sizes (stat -c %s) on the sender and bytes received for Table 2",
     "G_sizes.log", None, True),
    ("14_tamper_tests_1_2.png", "Part H, Tests 1-2: one character of the document changed; original passes, modified document FAILS",
     "H_tamper.log", list(range(0, 9)), True),
    ("15_tamper_test_3.png", "Part H, Test 3: one bit of each signature flipped at index UID mod length; all four FAIL",
     "H_tamper.log", list(range(9, 17)), True),
    ("16_tamper_test_4.png", "Part H, Test 4: receiver makes its own key pairs (independent ECDSA key) - verification with the wrong public key FAILS for all four",
     "H_tamper.log", list(range(17, 27)), True),
    ("17_bench_sender.png", "Part I: bench.py on the sender, run three times (results_run1/2/3.csv)",
     "I_bench_sender.log", None, True),
    ("18_median_run.png", "Part I: the median run (run 2) is kept as results.csv on the sender",
     "I_median.log", None, True),
    ("19_bench_receiver.png", "Part I: bench.py repeated on the receiver container (receiver results.csv)",
     "I_bench_receiver.log", None, True),
    ("20_plot.png", "Section 15: plot.py draws the seven graphs; docker cp copies graphs/ to the host",
     "S15_plot.log", None, True),
]

if __name__ == "__main__":
    os.makedirs("screenshots", exist_ok=True)
    for f in os.listdir("screenshots"):
        if f.endswith(".png"):
            os.remove(os.path.join("screenshots", f))
    for name, _, log, idx, fp in SHOTS:
        bl = parse(os.path.join("logs", log))
        render(bl if idx is None else [bl[i] for i in idx], os.path.join("screenshots", name), fp)
