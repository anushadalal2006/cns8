"""Build the Lab 10 (PGP and S/MIME) report (.docx + .pdf) in the order of Section 8 of the manual.

usage: python3 exp10/tools/make_report.py      (after render_terminal.py)
"""
import os
import re
import subprocess
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
EXP10 = os.path.dirname(HERE)
LOGS = os.path.join(EXP10, "logs")
TERM = os.path.join(EXP10, "terminal_screenshots")
REPORT = os.path.join(EXP10, "report")
NAME, UID = "Anusha Dalal", "2024300032"
sys.path.insert(0, HERE)
from render_terminal import parse  # noqa: E402


def log(name):
    return open(os.path.join(LOGS, name + ".log"), encoding="utf-8", errors="replace").read()


def grab(text, pattern, default="?"):
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else default


# ------------------------------------------------------------------ values from the run
ENV = log("00_environment")
OS_NAME = grab(ENV, r"^(?:Description:|PRETTY_NAME=)\s*\"?([^\"\n]+)")
KERNEL = grab(ENV, r"uname -r\n(\S+)")
GPG_VER = grab(ENV, r"^gpg \(GnuPG\) (\S+)")
GCRYPT = grab(ENV, r"^libgcrypt (\S+)")
OPENSSL_VER = grab(ENV, r"^(OpenSSL \S+ \d+ \w+ \d+)")
CPU = grab(ENV, r"^Model name:\s*(.+)$")
THREADS = grab(ENV, r"^CPU\(s\):\s*(\d+)")
RAM = grab(ENV, r"^Mem:\s+(\S+)").replace("Gi", " GiB")
RUN_DATE = grab(ENV, r"\$ date\n(.+)")
WHO = grab(ENV, r"^([\w.-]+@[\w.-]+):")
B4 = log("B4_export_import")
FPR_BOB = grab(B4, r"fingerprint bob-lab@example.test\npub[^\n]*\n\s+([0-9A-F ]{40,})")
FPR_ALICE = grab(B4, r"fingerprint alice-lab@example.test\npub[^\n]*\n\s+([0-9A-F ]{40,})")
C4 = log("C4_bob_cert")
ALICE_NB = grab(C4, r"alice.crt -noout -subject -issuer -dates\n(?:.*\n){2}notBefore=(.+)")
ALICE_NA = grab(C4, r"alice.crt -noout -subject -issuer -dates\n(?:.*\n){3}notAfter=(.+)")
ANSWERS = open(os.path.join(EXP10, "ANSWERS_LAB10.md"), encoding="utf-8").read()
ANSWERS = ANSWERS.replace(
    "fingerprints shown with `gpg --fingerprint` [from your run]",
    f"fingerprints shown with `gpg --fingerprint`: Alice {FPR_ALICE}, Bob {FPR_BOB}")
ANSWERS = ANSWERS.replace("valid 180 days [from your run]", f"valid 180 days ({ALICE_NB} to {ALICE_NA})")
DATE = RUN_DATE.split(" ")[2] + " " + RUN_DATE.split(" ")[1] + " " + RUN_DATE.split(" ")[-1] \
    if RUN_DATE != "?" else "?"

# ------------------------------------------------------------------ docx helpers
doc = Document()
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(11)
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2)
    s.top_margin = s.bottom_margin = Cm(1.8)
fig_no = 0


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def rich(p, text, size=10.5):
    for tok in re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)", text):
        if not tok:
            continue
        if tok.startswith("**"):
            for k, part_ in enumerate(re.split(r"`([^`]+)`", tok[2:-2])):
                if part_:
                    r = p.add_run(part_); r.bold = True; r.font.size = Pt(size)
                    if k % 2:
                        r.font.name = "Consolas"; r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            continue
        if tok.startswith("`"):
            r = p.add_run(tok[1:-1]); r.font.name = "Consolas"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        elif tok.startswith("*") and len(tok) > 2:
            r = p.add_run(tok[1:-1]); r.italic = True
        else:
            r = p.add_run(tok)
        r.font.size = Pt(size)


def para(text, size=10.5, italic=False, bold=False, align=None):
    p = doc.add_paragraph()
    rich(p, text, size)
    for r in p.runs:
        r.italic = r.italic or italic
        r.bold = r.bold or bold
    if align is not None:
        p.alignment = align
    return p


def table(head, rows, widths, size=9):
    t = doc.add_table(rows=1, cols=len(head))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(head):
        c = t.rows[0].cells[i]
        rich(c.paragraphs[0], h, size)
        for r in c.paragraphs[0].runs:
            r.bold = True
        shade(c, "D9E2F3")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            rich(cells[i].paragraphs[0], v, size)
    t.autofit = False
    for i, w in enumerate(widths):
        t._tbl.tblGrid.gridCol_lst[i].w = Cm(w)
        for r in t.rows:
            r.cells[i].width = Cm(w)
    for r in t.rows[:-1]:
        for c in r.cells:
            for p in c.paragraphs:
                p.paragraph_format.keep_with_next = True
    doc.add_paragraph()


def picture(path, max_w=17.0, max_h=21.5):
    w, h = Image.open(path).size
    doc.add_picture(path, width=Cm(min(max_w, max_h * w / h)))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


manifest = {}
for line in open(os.path.join(TERM, "manifest.txt")):
    heading, files = line.rstrip("\n").split("\t")
    files = files.split(",")
    stem = re.sub(r"(_\d)?\.png$", "", files[0])
    manifest[stem] = (heading, files)


def term(stem):
    global fig_no
    heading, files = manifest[stem]
    for k, f in enumerate(files):
        fig_no += 1
        cap = heading if len(files) == 1 else f"{heading} ({k + 1}/{len(files)})"
        h = doc.add_paragraph()
        r = h.add_run(f"Figure {fig_no}: {cap}")
        r.bold = True; r.font.size = Pt(10); r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
        h.paragraph_format.keep_with_next = True
        picture(os.path.join(TERM, f))


def box(title, lines=10):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    c = t.rows[0].cells[0]
    run = c.paragraphs[0].add_run("\n" * (lines // 2) + title + "\n[hand-written page attached]" + "\n" * (lines // 2))
    run.italic = True; run.font.size = Pt(11); run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    shade(c, "F3F3F3")
    doc.add_paragraph()


def section(title, intro=None):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading(title, level=1)
    if intro:
        para(intro)


def md_section(heading_regex, show_heading=True):
    """render one '## ...' section of the answers file (paragraphs, bullets, numbered lists, tables)"""
    m = re.search(r"^## (" + heading_regex + r"[^\n]*)\n(.*?)(?=^---$|^## |\Z)", ANSWERS, re.S | re.M)
    if show_heading:
        doc.add_heading(m.group(1), level=2)
    lines = m.group(2).strip("\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("> ") or line.startswith("*("):
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            n = len(rows[0])
            widths = {3: [4.2, 4.6, 8.2], 2: [4, 13]}.get(n, [17 / n] * n)
            table(rows[0], rows[1:], widths)
            continue
        mb = re.match(r"^(\s*)- (.*)$", line)
        if mb:
            p = doc.add_paragraph(style="List Bullet 2" if mb.group(1) else "List Bullet")
            rich(p, mb.group(2))
        else:
            p = doc.add_paragraph()
            rich(p, line)
        p.paragraph_format.space_after = Pt(4)
        i += 1


# ================================================================== title page
para("Bharatiya Vidya Bhavan's", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
para("SARDAR PATEL INSTITUTE OF TECHNOLOGY", bold=True, size=15, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Department of Computer Science and Engineering — Cryptography and Network Security Laboratory",
     size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Experiment: Secure E-mail using PGP and S/MIME", bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
table(["Field", "Value"], [["Name", NAME], ["UID", UID], ["Date of experiment", DATE]], [5, 12], size=10)
doc.add_heading("Aim", level=2)
para("To implement secure message exchange using Pretty Good Privacy (PGP/OpenPGP) and S/MIME, demonstrating "
     "public-key management, digital signatures, confidentiality through encryption, signature verification, "
     "decryption, and detection of message tampering.")
doc.add_heading("Contents (order of Section 8)", level=2)
table(["#", "Item"],
      [["1", "Hand-drawn PGP and S/MIME workflow diagrams"],
       ["2", "Table 1: execution environment"],
       ["3", "PGP evidence: key listings and fingerprints, export/import, detached signature, encryption/decryption, "
             "signed-and-encrypted message, tampering"],
       ["4", "S/MIME evidence: CA and user certificates, signed message, verification, encrypted message, decryption, "
             "tampering and untrusted-certificate results"],
       ["5", "Tables 2 and 3, comparative analysis, answers to the discussion questions, conclusion"],
       ["6", "Commands used and deviations caused by software versions"]], [1.2, 15.8], size=10)
para(f"Every terminal capture shows the name and UID line and the prompt of the machine used ({WHO}). "
     "No private keys are included in this report.", italic=True, size=9.5)

# ================================================================== 1. diagrams
section("1. Hand-drawn workflow diagrams (Part A)",
        "Drawn on paper before using the computer: Sender (Alice), Receiver (Bob), the insecure channel, key "
        "pairs/certificates, signing, encryption, decryption, verification, the ACCEPT/REJECT decision, an attacker "
        "modifying the message, and private keys never transmitted.")
box("PGP / OpenPGP workflow diagram", 16)
box("S/MIME workflow diagram", 16)

# ================================================================== 2. Table 1
section("2. Table 1: Execution environment")
table(["Parameter", "Observed value"],
      [["Operating system and version", f"{OS_NAME} (kernel {KERNEL})"],
       ["GnuPG version", f"GnuPG {GPG_VER} (libgcrypt {GCRYPT})"],
       ["OpenSSL version", OPENSSL_VER],
       ["CPU / RAM (optional)", f"{CPU}, {THREADS} logical CPUs / {RAM}"],
       ["Date of experiment", RUN_DATE]], [6, 11], size=10)
term("00_environment")

# ================================================================== 3. PGP evidence
section("3. PGP / OpenPGP evidence (Part B)",
        "Alice and Bob each have a separate GnuPG home directory, so each private key stays in its own keyring. "
        "Only public keys, the message, the signature and encrypted files are placed in the transfer folder.")
for stem in ("B1_gnupg", "B2_directories", "B3_alice_keygen", "B3_bob_keygen", "B4_export_import", "B5_sign",
             "B6_verify", "B7_encrypt_decrypt", "B7_sign_encrypt", "B8_tamper", "B9_wrong_private_key"):
    term(stem)

# ================================================================== 4. S/MIME evidence
section("4. S/MIME evidence (Part C)",
        "A local lab CA issues X.509 certificates for Alice and Bob; OpenSSL's smime command signs, verifies, encrypts "
        "and decrypts the message.")
for stem in ("C1_workspace", "C2_ca", "C3_alice_cert", "C4_bob_cert", "C4b_alice_cert_text", "C5_sign", "C6_verify",
             "C7_C8_encrypt_decrypt", "C9_sign_encrypt", "C10_tamper", "C10_untrusted"):
    term(stem)

# ================================================================== 5. tables, analysis, answers, conclusion
section("5. Results, comparative analysis, discussion and conclusion")
md_section(r"Table 2")
md_section(r"Table 3")
doc.add_heading("Comparative analysis", level=2)
table(["Parameter", "PGP / OpenPGP", "S/MIME"],
      [["Key / identity representation", "OpenPGP public key and fingerprint",
        "X.509 certificate containing public key and identity fields"],
       ["Trust model", "Often decentralized; fingerprints and user certifications",
        "Usually CA-issued certificate chain and validation"],
       ["Typical message representation", "OpenPGP packet / ASCII-armored data", "MIME with CMS/PKCS #7 structures"],
       ["Confidentiality mechanism", "Hybrid encryption; session key protected for recipient",
        "Hybrid encryption; content key protected for recipient"],
       ["Signature verification requires", "Correct sender public key and valid signature",
        "Sender certificate/public key, valid signature and applicable trust checks"],
       ["Common deployment", "OpenPGP-compatible clients and workflows",
        "Enterprise e-mail and certificate-based environments"],
       ["Observed challenge", "Public-key authenticity and trust decisions",
        "Certificate issuance, chain validation and lifecycle management"]], [4.2, 6.4, 6.4])
md_section(r"Comparative analysis", show_heading=False)
doc.add_heading("Answers to the discussion questions", level=2)
md_section(r"Discussion questions", show_heading=False)
doc.add_heading("Conclusion (150–200 words)", level=2)
box("Conclusion", 12)

# ================================================================== 6. commands and deviations
section("6. Commands used and deviations")
doc.add_heading("Commands used", level=2)
steps = [("Table 1", "00_environment"), ("B1", "B1_gnupg"), ("B2", "B2_directories"), ("B3 (Alice)", "B3_alice_keygen"),
         ("B3 (Bob)", "B3_bob_keygen"), ("B4", "B4_export_import"), ("B5", "B5_sign"), ("B6", "B6_verify"),
         ("B7", "B7_encrypt_decrypt"), ("B7 (sign + encrypt)", "B7_sign_encrypt"), ("B8", "B8_tamper"),
         ("Table 2 (optional)", "B9_wrong_private_key"), ("C1", "C1_workspace"), ("C2", "C2_ca"),
         ("C3", "C3_alice_cert"), ("C4", "C4_bob_cert"), ("C4 (details)", "C4b_alice_cert_text"), ("C5", "C5_sign"),
         ("C6", "C6_verify"), ("C7–C8", "C7_C8_encrypt_decrypt"), ("C9", "C9_sign_encrypt"), ("C10 (tamper)", "C10_tamper"),
         ("C10 (trust)", "C10_untrusted")]
rows = []
for label, name in steps:
    cmds = [" ".join(b["cmd"]) for b in parse(os.path.join(LOGS, name + ".log")) if not b["cmd"][0].startswith('echo "Name')]
    rows.append([label, "\n".join(cmds)])
t = doc.add_table(rows=1, cols=2)
t.style = "Table Grid"
for i, h in enumerate(("Step", "Commands")):
    run = t.rows[0].cells[i].paragraphs[0].add_run(h); run.bold = True; run.font.size = Pt(9)
    shade(t.rows[0].cells[i], "D9E2F3")
for label, cmds in rows:
    cells = t.add_row().cells
    r = cells[0].paragraphs[0].add_run(label); r.font.size = Pt(9); r.bold = True
    for k, c in enumerate(cmds.split("\n")):
        p = cells[1].paragraphs[0] if k == 0 else cells[1].add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(c); r.font.size = Pt(7.5); r.font.name = "Consolas"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
t.autofit = False
for i, w in enumerate((2.6, 14.4)):
    t._tbl.tblGrid.gridCol_lst[i].w = Cm(w)
    for r in t.rows:
        r.cells[i].width = Cm(w)
doc.add_paragraph()
doc.add_heading("Deviations caused by software versions or the environment", level=2)
for d in [
    "**Passphrase prompt in the terminal:** without a graphical desktop, GnuPG's pinentry pop-up is not available, "
    "so each keyring's gpg.conf contains `pinentry-mode loopback`; GnuPG then asks for the passphrase directly in the "
    "terminal (the passphrase is not echoed). The key-generation answers were exactly those in the manual "
    "(RSA and RSA, 3072 bits, expiry 1 year, the given names and e-mail addresses).",
    "**\"Use this key anyway? (y/N)\":** when Alice encrypts for Bob, GnuPG 2.4 asks this because Bob's imported key "
    "is not yet certified; it was answered y after the fingerprint was compared (Step B4).",
    "**C10 edit with sed instead of a text editor:** one character of the signed body was changed with `sed` "
    "(\"test\" to \"tost\"); `diff` shows that only that line changed and the MIME structure is intact.",
    "**Certificate extensions:** in OpenSSL 3.0, `openssl x509 -req` does not copy extensions from the CSR unless "
    "`-copy_extensions copy` is given, so alice.crt and bob.crt contain no keyUsage/extendedKeyUsage. S/MIME still "
    "works, because a certificate without these extensions is not restricted.",
    "**Decrypted file vs message.txt:** the `-text` option wraps the message in a `Content-Type: text/plain` MIME "
    "header and S/MIME uses CRLF line endings, so the files differ by the header and line endings only; the "
    "message body was compared with `tail -n +3 | tr -d '\\r' | diff` and is identical.",
    "**Untrusted CA test:** in addition to omitting -CAfile, a second unrelated CA (\"Some Other CA\") was used, "
    "and `-noverify` was run to show that the failure is a certificate-trust failure, not a content failure.",
]:
    p = doc.add_paragraph(style="List Bullet")
    rich(p, d, 10)

os.makedirs(REPORT, exist_ok=True)
out = os.path.join(REPORT, f"Lab10_PGP_SMIME_{UID}_{NAME.replace(' ', '_')}.docx")
doc.save(out)
subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", REPORT, out], check=True, capture_output=True)
print("wrote", out, "and", out[:-5] + ".pdf")
