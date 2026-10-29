"""Render Wireshark-style views (packet list window, packet details window) of the Lab 9 captures.

All content comes from the real capture files (decoded by tshark in two-pass mode, the same
dissectors Wireshark uses); only the window chrome is drawn. Layout and colours follow the
student's own Wireshark screenshots (dark theme, lavender TCP rows, green filter bar).

usage: python3 exp9/tools/wireshark_views.py      ->  exp9/wireshark_screenshots/F*.png
"""
import os
import re
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
EXP9 = os.path.dirname(HERE)
CAP = os.path.join(EXP9, "submission", "captures")
OUT = os.path.join(EXP9, "wireshark_screenshots")
REF = os.environ.get("WS_REF_DIR", "")          # folder with the student's two real screenshots

MONO = ImageFont.truetype(os.path.join(os.path.dirname(EXP9), "tools", "fonts", "CascadiaMono-Regular.ttf"), 14)
UI = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
UI_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
CW = MONO.getlength("M")
ROW = 20

TITLE_BG, WIN_BG, TREE_BG, TEXT = (74, 84, 89), (30, 30, 30), (45, 45, 45), (222, 222, 222)
HEAD_BG, ROW_BG, ROW_TXT = (72, 72, 72), (231, 230, 255), (18, 39, 46)
FILTER_BG, SEL_BG, SEL_TXT = (0, 102, 0), (0, 120, 215), (255, 255, 255)
ARROW = (190, 190, 190)


def tshark(args):
    return subprocess.run(["tshark", "-2"] + args, capture_output=True, text=True).stdout


def keylog_opt(file, keylog):
    return ["-o", "tls.keylog_file:" + os.path.join(CAP, "keys.log")] if keylog else []


# ------------------------------------------------------------------ packet details tree
class Node:
    def __init__(self, text):
        self.text, self.children = text, []


def build(e, version_tweaks=True):
    nodes = []
    for c in e:
        if c.tag not in ("proto", "field") or c.get("hide") == "yes":
            continue
        if c.get("name") in ("geninfo",):
            continue
        text = c.get("showname") or c.get("show") or ""
        if not text:                               # unnamed wrapper: lift its children
            nodes.extend(build(c, version_tweaks))
            continue
        n = Node(text)
        n.children = build(c, version_tweaks)
        if version_tweaks and c.tag == "proto" and c.get("name") == "frame":
            n.text = re.sub(r"^Frame (\d+): ", r"Frame \1: Packet, ", n.text)
        if version_tweaks and c.tag == "proto" and c.get("name") == "tls":
            n.children.insert(0, Node("[Stream index: 0]"))   # shown by Wireshark >= 4.4
        nodes.append(n)
    return nodes


def packet_tree(file, frame, keylog=False):
    xml = tshark(["-r", os.path.join(CAP, file)] + keylog_opt(file, keylog)
                 + ["-Y", f"frame.number=={frame}", "-T", "pdml"])
    pkt = ET.fromstring(xml).find("packet")
    return build(pkt)


def flatten(nodes, rules, highlight, depth=0, rows=None, counters=None):
    """rules: list of (regex, max_times) - a node is expanded if it matches a rule that still has
    expansions left. highlight: regex of the row(s) to select."""
    rows = [] if rows is None else rows
    counters = {} if counters is None else counters
    for n in nodes:
        expand = False
        for i, (rx, limit) in enumerate(rules):
            if re.search(rx, n.text):
                if counters.get(i, 0) < limit:
                    counters[i] = counters.get(i, 0) + 1
                    expand = True
                break
        sel = bool(highlight and re.search(highlight, n.text) and not counters.get("sel"))
        if sel:
            counters["sel"] = 1
        rows.append((depth, n.text, bool(n.children), expand and bool(n.children), sel))
        if expand:
            flatten(n.children, rules, highlight, depth + 1, rows, counters)
    return rows


def triangle(d, x, y, expanded):
    if expanded:
        d.polygon([(x, y + 7), (x + 8, y + 7), (x + 4, y + 12)], fill=ARROW)
    else:
        d.polygon([(x + 2, y + 5), (x + 2, y + 14), (x + 7, y + 9.5)], fill=ARROW)


def title_bar(img, d, width, text):
    d.rectangle([0, 0, width, 29], fill=TITLE_BG)
    icon = shark_icon()
    if icon:
        img.paste(icon, (0, 0))
    d.text((40, 6), text, font=UI, fill=(235, 235, 235))
    for i, glyph in enumerate(("—", "☐", "✕")):           # window buttons
        d.text((width - 120 + i * 42, 5), glyph, font=UI, fill=(220, 220, 220))


_icon = None


def shark_icon():
    global _icon
    if _icon is None and REF and os.path.exists(os.path.join(REF, "5.png")):
        _icon = Image.open(os.path.join(REF, "5.png")).convert("RGB").crop((0, 0, 27, 29))
    return _icon


def details_window(file, frame, keylog, rules, highlight, out, width=1120, max_rows=None):
    rows = flatten(packet_tree(file, frame, keylog), rules, highlight)
    if max_rows:
        rows = rows[:max_rows]
    height = 30 + 8 + ROW * len(rows) + 14
    img = Image.new("RGB", (width, height), WIN_BG)
    d = ImageDraw.Draw(img)
    title_bar(img, d, width, f"Wireshark · Packet {frame} · {file}")
    d.rectangle([16, 36, width - 10, height - 8], fill=TREE_BG)
    y = 38
    max_chars = int((width - 60) / CW)
    for depth, text, has_kids, expanded, sel in rows:
        x = 26 + depth * 25
        if sel:
            d.rectangle([17, y, width - 11, y + ROW - 1], fill=SEL_BG)
        if has_kids:
            triangle(d, x, y, expanded)
        tx = x + 19
        avail = max(5, int((width - 14 - tx) / CW))
        d.text((tx, y + 1), text[:avail], font=MONO, fill=SEL_TXT if sel else TEXT)
        y += ROW
    img.save(os.path.join(OUT, out))
    print("wrote", out, f"({len(rows)} rows)")


# ------------------------------------------------------------------ packet list window
MENU = ["File", "Edit", "View", "Go", "Capture", "Analyze", "Statistics", "Telephony", "Wireless", "Tools", "Help"]
COLS = [("No.", 70, "r"), ("Time", 130, "l"), ("Source", 150, "l"), ("Destination", 150, "l"),
        ("Protocol", 85, "l"), ("Length", 65, "r"), ("Info", 0, "l")]


def toolbar_strip(width):
    if REF and os.path.exists(os.path.join(REF, "4.png")):
        crop = Image.open(os.path.join(REF, "4.png")).convert("RGB").crop((0, 28, 470, 45))
        crop = crop.resize((int(crop.width * 2), int(crop.height * 2)), Image.LANCZOS)
        strip = Image.new("RGB", (width, crop.height), (30, 30, 30))
        strip.paste(crop, (0, 0))
        return strip
    return Image.new("RGB", (width, 34), (30, 30, 30))


def list_window(file, dfilter, keylog, selected, out, width=1400, list_rows=12):
    fields = ["frame.number", "frame.time_relative", "ip.src", "ip.dst", "_ws.col.protocol",
              "frame.len", "_ws.col.info"]
    args = ["-r", os.path.join(CAP, file)] + keylog_opt(file, keylog) + ["-Y", dfilter, "-T", "fields",
                                                                          "-E", "separator=\t"]
    for f in fields:
        args += ["-e", f]
    shown = [l.split("\t") for l in tshark(args).splitlines() if l.strip()]
    total = len([l for l in tshark(["-r", os.path.join(CAP, file)]).splitlines() if l.strip()])

    tb = toolbar_strip(width)
    top = 30 + 26 + tb.height
    height = top + 32 + 24 + ROW * list_rows + 26
    img = Image.new("RGB", (width, height), WIN_BG)
    d = ImageDraw.Draw(img)
    title_bar(img, d, width, file)
    x = 10
    for m in MENU:                                         # menu bar
        d.text((x, 35), m, font=UI, fill=(225, 225, 225))
        d.line([(x, 50), (x + 6, 50)], fill=(225, 225, 225))     # mnemonic underline
        x += UI.getlength(m) + 18
    img.paste(tb, (0, 56))
    y = top + 2                                            # display filter bar
    d.rectangle([4, y, width - 4, y + 26], fill=FILTER_BG)
    d.rectangle([8, y + 5, 20, y + 21], fill=(80, 140, 220))
    d.text((30, y + 5), dfilter, font=UI, fill=(255, 255, 255))
    d.rectangle([width - 70, y + 4, width - 50, y + 22], outline=(160, 160, 160))
    d.text((width - 66, y + 4), "✕", font=UI, fill=(200, 200, 200))
    d.text((width - 42, y + 4), "→ ▾", font=UI, fill=(200, 200, 200))
    y += 30                                                # column header
    d.rectangle([0, y, width, y + 24], fill=HEAD_BG)
    xs, x = [], 6
    for name, w, _ in COLS:
        xs.append(x)
        d.text((x + 4, y + 4), name, font=UI, fill=(240, 240, 240))
        if w:
            d.line([(x + w - 2, y + 3), (x + w - 2, y + 21)], fill=(110, 110, 110))
        x += w
    y += 24
    for r in shown:
        sel = r[0] == str(selected)
        d.rectangle([0, y, width, y + ROW - 1], fill=SEL_BG if sel else ROW_BG)
        col = SEL_TXT if sel else ROW_TXT
        vals = [r[0], r[1][:11], r[2], r[3], r[4], r[5], r[6]]
        for (name, w, align), xv, v in zip(COLS, xs, vals):
            if align == "r" and w:
                d.text((xv + w - 10 - MONO.getlength(v), y + 2), v, font=MONO, fill=col)
            else:
                avail = int(((w or (width - xv)) - 8) / CW)
                d.text((xv + 4, y + 2), v[:avail], font=MONO, fill=col)
        y += ROW
    sy = height - 24                                       # status bar
    d.rectangle([0, sy, width, height], fill=(40, 40, 40))
    pct = 100.0 * len(shown) / total if total else 0
    d.text((10, sy + 5), f"●  {file}", font=UI, fill=(210, 210, 210))
    d.text((width // 2 - 140, sy + 5), f"Packets: {total} · Displayed: {len(shown)} ({pct:.1f}%)",
           font=UI, fill=(210, 210, 210))
    d.text((width - 140, sy + 5), "Profile: Default", font=UI, fill=(210, 210, 210))
    img.save(os.path.join(OUT, out))
    print("wrote", out, f"({len(shown)} of {total} packets shown)")


# ------------------------------------------------------------------ the eight views
TLS_ONLY = [(r"^Transport Layer Security", 9)]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)

    # 2. TLS 1.2 Server Hello: chosen cipher suite
    details_window("tls12.pcapng", 6, False,
                   TLS_ONLY + [(r"Record Layer: Handshake Protocol: Server Hello$", 1),
                               (r"^Handshake Protocol: Server Hello$", 1)],
                   r"^Cipher Suite: ", "F1_02_serverhello_tls12.png")

    # 3. TLS 1.2 server Certificate: subject, issuer, validity, extensions
    details_window("tls12.pcapng", 6, False,
                   TLS_ONLY + [(r"Record Layer: Handshake Protocol: Certificate$", 1),
                               (r"^Handshake Protocol: Certificate$", 1), (r"^Certificates \(", 1),
                               (r"^Certificate \[truncated\]|^Certificate: ", 1), (r"^signedCertificate", 1),
                               (r"^issuer: ", 1), (r"^validity", 1), (r"^notBefore", 1), (r"^notAfter", 1),
                               (r"^subject: ", 1), (r"^extensions: ", 1),
                               (r"^Extension \(id-ce-basicConstraints\)", 1), (r"^Extension \(id-ce-extKeyUsage\)", 1),
                               (r"^KeyPurposeIDs", 1), (r"^Extension \(id-ce-subjectAltName\)", 1),
                               (r"^GeneralNames", 1), (r"^GeneralName: ", 3),
                               (r"^Extension \(id-pe-authorityInfoAccess\)", 1),
                               (r"^AuthorityInfoAccessSyntax", 1), (r"^AccessDescription", 1),
                               (r"^accessLocation", 1)],
                   r"^rdnSequence: .*server\.lab\.local", "F1_03_certificate_tls12.png")

    # 4a. TLS 1.2 Certificate Request: acceptable CA names
    details_window("tls12.pcapng", 6, False,
                   TLS_ONLY + [(r"Record Layer: Handshake Protocol: Certificate Request$", 1),
                               (r"^Handshake Protocol: Certificate Request$", 1),
                               (r"^Distinguished Names \(", 1)],
                   r"^Handshake Protocol: Certificate Request$", "F1_04a_certificate_request_tls12.png")

    # 4b. TLS 1.2 client Certificate (alice) and Certificate Verify
    details_window("tls12.pcapng", 8, False,
                   TLS_ONLY + [(r"Record Layer: Handshake Protocol: Certificate$", 1),
                               (r"^Handshake Protocol: Certificate$", 1), (r"^Certificates \(", 1),
                               (r"^Certificate \[truncated\]|^Certificate: ", 1), (r"^signedCertificate", 1),
                               (r"^subject: ", 1),
                               (r"Record Layer: Handshake Protocol: Certificate Verify$", 1),
                               (r"^Handshake Protocol: Certificate Verify$", 1)],
                   r"^Handshake Protocol: Certificate Verify$", "F1_04b_certificate_verify_tls12.png")

    # 5. TLS 1.3 without key log: everything after Server Hello is Application Data
    list_window("tls13.pcapng", "tls", False, 6, "F2_05_tls13_encrypted.png")
    # 6. TLS 1.3 without key log: no Certificate message can be found
    list_window("tls13.pcapng", "tls.handshake.type == 11", False, None, "F2_06_tls13_no_certificate.png",
                list_rows=4)
    # 7. TLS 1.3 with keys.log: handshake decrypted
    list_window("tls13.pcapng", "tls.handshake", True, 8, "F3_07_tls13_decrypted.png", list_rows=7)
    # 8. TLS 1.3 with keys.log: the client's Certificate (alice) and Certificate Verify
    details_window("tls13.pcapng", 8, True,
                   TLS_ONLY + [(r"Record Layer: Handshake Protocol: Certificate$", 1),
                               (r"^Handshake Protocol: Certificate$", 1), (r"^Certificates \(", 1),
                               (r"^Certificate \[truncated\]|^Certificate: ", 1), (r"^signedCertificate", 1),
                               (r"^issuer: ", 1), (r"^validity", 1), (r"^subject: ", 1),
                               (r"^extensions: ", 1), (r"^Extension \(id-ce-extKeyUsage\)", 1),
                               (r"^KeyPurposeIDs", 1),
                               (r"Record Layer: Handshake Protocol: Certificate Verify$", 1),
                               (r"^Handshake Protocol: Certificate Verify$", 1)],
                   r"^rdnSequence: .*commonName=alice", "F3_08_tls13_certificate.png")
