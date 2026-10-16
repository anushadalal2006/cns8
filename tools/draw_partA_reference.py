"""Draws a REFERENCE version of the Part A digital-signature diagram (all 8 required elements).

Part A must be hand-drawn on paper (pen + ruler); this figure is only a guide to copy from.
usage: python3 tools/draw_partA_reference.py  ->  report/partA_reference_diagram.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

fig, ax = plt.subplots(figsize=(16, 10.5))
ax.set_xlim(0, 160); ax.set_ylim(0, 105); ax.axis("off")


def box(x, y, w, h, text, fc="#ffffff", ec="black", ls="-", fs=11, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4", fc=fc, ec=ec, ls=ls, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")


def arrow(x1, y1, x2, y2, text="", ls="-", color="black", tx=0, ty=1.5, fs=10, rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                                 lw=1.5, ls=ls, color=color, connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((x1 + x2) / 2 + tx, (y1 + y2) / 2 + ty, text, ha="center", fontsize=fs, color=color)


ax.text(80, 102, "Digital-signature model: Sender (Alice) -> insecure channel -> Receiver (Bob)",
        ha="center", fontsize=15, fontweight="bold")
ax.text(158, 102, "Name: Anusha Dalal\nUID: 2024300032\nDate: ____", ha="right", va="top", fontsize=10)

# (1) parties and channel
ax.add_patch(FancyBboxPatch((2, 4), 52, 90, boxstyle="round,pad=0.5", fc="#eef3fb", ec="#2a6fb0", lw=2))
ax.text(28, 91, "SENDER (Alice)", ha="center", fontsize=14, fontweight="bold", color="#2a6fb0")
ax.add_patch(FancyBboxPatch((106, 4), 52, 90, boxstyle="round,pad=0.5", fc="#eef8f1", ec="#2e8b57", lw=2))
ax.text(132, 91, "RECEIVER (Bob)", ha="center", fontsize=14, fontweight="bold", color="#2e8b57")
ax.add_patch(FancyBboxPatch((60, 4), 40, 90, boxstyle="round,pad=0.5", fc="#fafafa", ec="#888", ls="--", lw=1.5))
ax.text(80, 91, "INSECURE CHANNEL", ha="center", fontsize=12, fontweight="bold", color="#555")

# (2) message and hash, (3) key pair, (4) signing - sender side
box(8, 78, 40, 7, "Message M", fc="#fff")
box(8, 64, 40, 7, "Hash function H( )\ndigest h = H(M)")
arrow(28, 77.5, 28, 71.6)
box(6, 46, 20, 9, "Private key SK$_A$\n(kept SECRET)", fc="#fde8e8", ec="#b02a2a")
box(30, 46, 20, 9, "Public key PK$_A$", fc="#e8f0fd", ec="#2a6fb0")
ax.text(28, 57.5, "KeyGen() -> (PK$_A$, SK$_A$)", ha="center", fontsize=10, style="italic")
box(8, 28, 40, 9, "S = Sign(SK$_A$, h)", bold=True)
arrow(28, 63.5, 28, 37.6)
arrow(16, 45.5, 22, 37.6, ls="--", color="#b02a2a")        # SK dashed: never leaves Alice
ax.text(8, 41.5, "dashed: SK$_A$\nstays with Alice", fontsize=8.5, color="#b02a2a")
box(8, 12, 40, 7, "Output pair (M || S)\n|| = concatenation", fc="#fffbe6")
arrow(28, 27.5, 28, 19.6)

# (5) transfer of (M || S) and public-key distribution
# (M || S) travels along the bottom of the channel, then up into Bob's inbox
ax.plot([48.6, 104, 104], [15.5, 15.5, 75.5], color="black", lw=1.5)
arrow(104, 75.5, 111.6, 75.5)
ax.text(70, 12.2, "(M || S)", ha="center", fontsize=12, fontweight="bold")
arrow(50.6, 50.5, 111.6, 45, color="#2a6fb0")
ax.text(80, 50.5, "PK$_A$ (public key distribution)", ha="center", fontsize=10, color="#2a6fb0")
ax.text(80, 58.5, "SK$_A$ is NEVER sent", ha="center", fontsize=12, fontweight="bold", color="#b02a2a",
        bbox=dict(fc="white", ec="#b02a2a"))

# (8) attacker
box(64, 25, 32, 11, "Mallory (attacker)\nmodifies M -> M'", fc="#fde8e8", ec="#b02a2a", ls="--")
arrow(88, 24.5, 88, 16.3, color="#b02a2a")
ax.text(80, 7, "Attack: M' != M  =>  h' != h\n=>  Verify fails  =>  REJECT", ha="center",
        fontsize=10, color="#b02a2a", fontweight="bold")

# (6) receiver side
box(112, 72, 40, 7, "Received M' and S")
box(112, 58, 40, 8, "recompute h' = H(M')")
arrow(132, 71.5, 132, 66.6)
box(112, 40, 40, 10, "Verify(PK$_A$, h', S)", bold=True)
arrow(132, 57.5, 132, 50.6)
# (7) decision
box(112, 24, 40, 8, "Decision: h' matches S under PK$_A$ ?", fc="#fffbe6")
arrow(132, 39.5, 132, 32.6)
box(110, 8, 19, 8, "ACCEPT\n(valid)", fc="#dff3e6", ec="#2e8b57", bold=True)
box(135, 8, 19, 8, "REJECT\n(invalid)", fc="#fde8e8", ec="#b02a2a", bold=True)
arrow(124, 23.5, 120, 16.6, "yes", tx=-3, ty=0)
arrow(140, 23.5, 144, 16.6, "no", tx=3, ty=0)

ax.text(80, 0.5, "Symbols: M message, H hash function, h digest, S signature, SK private key, "
        "PK public key, || concatenation.  REFERENCE ONLY - Part A must be drawn by hand.",
        ha="center", fontsize=9, color="#555")
fig.tight_layout()
fig.savefig("report/partA_reference_diagram.png", dpi=150)
print("wrote report/partA_reference_diagram.png")
