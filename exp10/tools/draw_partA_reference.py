"""Reference drawings of the two Part A workflows (PGP and S/MIME) to copy by hand.

Part A must be drawn on paper; these figures only show the required elements.
usage: python3 exp10/tools/draw_partA_reference.py  ->  exp10/report/partA_reference_{pgp,smime}.png
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "report")


def diagram(title, sender_steps, receiver_steps, channel_items, keys_note, out):
    fig, ax = plt.subplots(figsize=(16, 9.6))
    ax.set_xlim(0, 160); ax.set_ylim(0, 96); ax.axis("off")

    def box(x, y, w, h, text, fc="white", ec="black", ls="-", bold=False, fs=10.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4", fc=fc, ec=ec, ls=ls, lw=1.4))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
                fontweight="bold" if bold else "normal")

    def arrow(x1, y1, x2, y2, color="black", ls="-"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=15, lw=1.5,
                                     color=color, ls=ls))

    ax.text(80, 93, title, ha="center", fontsize=15, fontweight="bold")
    ax.text(158, 93, "Name: Anusha Dalal\nUID: 2024300032\nDate: ____", ha="right", va="top", fontsize=9)
    ax.add_patch(FancyBboxPatch((2, 4), 50, 82, boxstyle="round,pad=0.5", fc="#eef3fb", ec="#2a6fb0", lw=2))
    ax.text(27, 82.5, "SENDER (Alice)", ha="center", fontsize=13, fontweight="bold", color="#2a6fb0")
    ax.add_patch(FancyBboxPatch((108, 4), 50, 82, boxstyle="round,pad=0.5", fc="#eef8f1", ec="#2e8b57", lw=2))
    ax.text(133, 82.5, "RECEIVER (Bob)", ha="center", fontsize=13, fontweight="bold", color="#2e8b57")
    ax.add_patch(FancyBboxPatch((58, 4), 44, 82, boxstyle="round,pad=0.5", fc="#fafafa", ec="#888", ls="--", lw=1.5))
    ax.text(80, 82.5, "INSECURE CHANNEL\n(transfer folder / e-mail)", ha="center", va="center", fontsize=11,
            fontweight="bold", color="#555")

    y = 72
    for i, (text, fc) in enumerate(sender_steps):
        box(6, y, 42, 7, text, fc=fc, bold=i in (1, 2))
        if i:
            arrow(27, y + 9.2, 27, y + 7.6)
        y -= 11.5
    y = 72
    for i, (text, fc) in enumerate(receiver_steps):
        box(112, y, 42, 7, text, fc=fc, bold=i in (1, 2))
        if i:
            arrow(133, y + 9.2, 133, y + 7.6)
        y -= 11.5
    box(110, 6, 20, 6.5, "ACCEPT\n(valid)", fc="#dff3e6", ec="#2e8b57", bold=True)
    box(136, 6, 20, 6.5, "REJECT\n(invalid)", fc="#fde8e8", ec="#b02a2a", bold=True)
    yb = lambda i: 72 - 11.5 * i + 3.5                 # vertical centre of step box i
    arrow(127, 37, 121, 13)                             # decision -> ACCEPT / REJECT
    arrow(139, 37, 145, 13)

    # public keys / certificates: Alice's key box -> Bob's Verify box (dashed blue)
    arrow(48.5, yb(0), 111.5, yb(2), color="#2a6fb0", ls="--")
    ax.text(80, yb(0) - 9.5, channel_items[1], ha="center", fontsize=9.5, color="#2a6fb0")
    # the message: Alice's Send box -> Bob's Decrypt box
    arrow(48.5, yb(3), 111.5, yb(1), color="black")
    ax.text(80, (yb(3) + yb(1)) / 2 - 5.5, channel_items[0], ha="center", fontsize=10.5, fontweight="bold",
            rotation=20)
    ax.text(80, 76.5, "PRIVATE KEYS ARE NEVER SENT", ha="center", fontsize=11, fontweight="bold",
            color="#b02a2a", bbox=dict(fc="white", ec="#b02a2a"))
    box(63, 14, 34, 9, "Mallory (attacker)\nmodifies the message", fc="#fde8e8", ec="#b02a2a", ls="--")
    ax.text(80, 8, "modified content -> signature\nverification FAILS -> REJECT", ha="center", fontsize=9.5,
            color="#b02a2a", fontweight="bold")
    xm = 88
    arrow(xm, 23.5, xm, yb(3) + (yb(1) - yb(3)) * (xm - 48.5) / 63 - 0.8, color="#b02a2a")
    ax.text(80, 0.3, keys_note + "   REFERENCE ONLY - Part A must be drawn by hand.", ha="center",
            fontsize=8.5, color="#555")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    diagram("PGP / OpenPGP secure e-mail workflow",
            [("Key pair: Alice private key (secret)\n+ public key (shared, fingerprint checked)", "#fff8e1"),
             ("Sign: hash(message) signed\nwith ALICE's PRIVATE key", "#fde8e8"),
             ("Encrypt: random session key encrypts message;\nsession key encrypted with BOB's PUBLIC key", "#e8f0fd"),
             ("Send: ASCII-armored .pgp\n(signed + encrypted)", "white"),
             ("(Bob's public key was imported earlier;\nfingerprint verified on a trusted channel)", "#f5f5f5")],
            [("Key pair: Bob private key (secret)\n+ public key (shared)", "#fff8e1"),
             ("Decrypt: BOB's PRIVATE key recovers\nthe session key, then the message", "#e8f0fd"),
             ("Verify: signature checked with\nALICE's PUBLIC key", "#fde8e8"),
             ("Decision: good signature?\n(trust warning reported separately)", "#fffbe6")],
            ["signed + encrypted message", "public keys only\n(.asc, imported, fingerprints compared)"],
            "Decentralised trust: users exchange public keys and compare fingerprints.",
            os.path.join(OUT, "partA_reference_pgp.png"))
    diagram("S/MIME secure e-mail workflow",
            [("Lab CA issues X.509 certificates\nfor Alice and Bob (CA trusted by both)", "#fff8e1"),
             ("Sign: Alice signs with the PRIVATE key\nbelonging to her certificate", "#fde8e8"),
             ("Encrypt: content key encrypts the signed MIME;\ncontent key encrypted with BOB's CERTIFICATE", "#e8f0fd"),
             ("Send: smime.p7m (CMS / PKCS #7,\nenveloped data)", "white"),
             ("Alice's certificate travels inside\nthe signed message", "#f5f5f5")],
            [("Bob holds his private key and\ntrusts the lab CA certificate", "#fff8e1"),
             ("Decrypt: BOB's PRIVATE key recovers\nthe content key, then the signed MIME", "#e8f0fd"),
             ("Verify: signature with ALICE's certificate;\ncertificate chain checked against the CA", "#fde8e8"),
             ("Decision: signature valid AND\ncertificate trusted?", "#fffbe6")],
            ["signed + encrypted message", "certificates only\n(public keys + identity, signed by the CA)"],
            "Hierarchical trust: certificates are validated through a CA chain.",
            os.path.join(OUT, "partA_reference_smime.png"))
