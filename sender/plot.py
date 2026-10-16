"""plot.py [results.csv] [document.txt] - draw the seven graphs of Section 15 into graphs/.

Every graph has a title, axis labels with units, a legend where required and the execution
environment in the caption (read from environment.txt if present). A logarithmic y-axis is
used wherever the values differ by orders of magnitude.
"""
import os
import platform
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import ALG_ORDER, ALGS, UID

CSV = sys.argv[1] if len(sys.argv) > 1 else "results.csv"
DOC = sys.argv[2] if len(sys.argv) > 2 else os.path.join("outbox", "document.txt")
OUT = "graphs"
COLORS = {"ecdsa": "#2a6fb0", "rsapss": "#7a4fa3", "mldsa": "#2e8b57", "slhdsa": "#d0782a"}


def environment_caption():
    if os.path.exists("environment.txt"):
        with open("environment.txt") as f:
            env = " | ".join(line.strip() for line in f if line.strip())
    else:
        env = f"{platform.processor() or platform.machine()} | {platform.platform()}"
    return f"UID {UID} | Environment: {env}"


CAPTION = environment_caption()

df = pd.read_csv(CSV, dtype={"uid": str})
labels = [ALGS[a]["label"] for a in ALG_ORDER]
colors = [COLORS[a] for a in ALG_ORDER]
x = np.arange(len(ALG_ORDER))


def row(alg, op):
    return df[(df.algorithm == alg) & (df.operation == op)].iloc[0]


def sizes(col):
    return [int(row(a, "sign")[col]) for a in ALG_ORDER]


pk, sk, sig = sizes("public_key_bytes"), sizes("private_key_bytes"), sizes("signature_bytes")
doc = os.path.getsize(DOC)


def finish(fig, ax, name, title, ylabel, log=False, legend=False):
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Signature algorithm")
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    if log:
        ax.set_yscale("log")
    ax.grid(axis="y", which="both", alpha=0.3)
    ax.set_axisbelow(True)
    if legend:
        ax.legend()
    fig.text(0.5, 0.01, CAPTION, ha="center", va="bottom", fontsize=6.5, wrap=True, color="#444")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[plot] wrote {path}")


def annotate(ax, bars, fmt="{:,.0f}", tops=None):
    for i, b in enumerate(bars):
        h = b.get_height()
        y = tops[i] if tops is not None else h
        ax.annotate(fmt.format(h), (b.get_x() + b.get_width() / 2, y), ha="center",
                    va="bottom", fontsize=8, xytext=(0, 2), textcoords="offset points")


def bar_with_err(op, name, title):
    mean = [row(a, op).mean_ms for a in ALG_ORDER]
    std = [row(a, op).std_ms for a in ALG_ORDER]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(x, mean, yerr=std, capsize=6, color=colors, edgecolor="black",
                  error_kw={"elinewidth": 1.2})
    annotate(ax, bars, "{:.3f}", tops=[m + sd for m, sd in zip(mean, std)])
    n = int(row(ALG_ORDER[0], op).runs)
    finish(fig, ax, name, title, f"Mean time per operation (ms, log scale), n={n}", log=True)


def main():
    os.makedirs(OUT, exist_ok=True)

    # Graph 1 - grouped bar: public and private key sizes
    fig, ax = plt.subplots(figsize=(8, 5))
    w = 0.38
    b1 = ax.bar(x - w / 2, pk, w, label="Public key", color="#2a6fb0", edgecolor="black")
    b2 = ax.bar(x + w / 2, sk, w, label="Private key", color="#d0782a", edgecolor="black")
    annotate(ax, b1); annotate(ax, b2)
    finish(fig, ax, "graph1_key_sizes.png", "Graph 1: Public- and private-key size",
           "Size (bytes, log scale)", log=True, legend=True)

    # Graph 2 - bar: signature size
    fig, ax = plt.subplots(figsize=(8, 5))
    annotate(ax, ax.bar(x, sig, color=colors, edgecolor="black"))
    finish(fig, ax, "graph2_signature_size.png", "Graph 2: Signature size",
           "Signature size (bytes, log scale)", log=True)

    # Graphs 3, 4 - bars with error bars (std)
    bar_with_err("sign", "graph3_signing_time.png",
                 "Graph 3: Average signing time (1024-byte message), error bar = std")
    bar_with_err("verify", "graph4_verification_time.png",
                 "Graph 4: Average verification time (1024-byte message), error bar = std")

    # Graph 5 - bar: key-generation time
    fig, ax = plt.subplots(figsize=(8, 5))
    kg = [row(a, "keygen").mean_ms for a in ALG_ORDER]
    annotate(ax, ax.bar(x, kg, color=colors, edgecolor="black"), "{:.3f}")
    finish(fig, ax, "graph5_keygen_time.png", "Graph 5: Average key-generation time",
           f"Mean time per key pair (ms, log scale), n={int(row('ecdsa', 'keygen').runs)}", log=True)

    # Graph 6 - stacked bar: document + signature + public key
    fig, ax = plt.subplots(figsize=(8, 5))
    d = np.array([doc] * len(ALG_ORDER)); s = np.array(sig); p = np.array(pk)
    ax.bar(x, d, label=f"Document ({doc} B)", color="#999999", edgecolor="black")
    ax.bar(x, s, bottom=d, label="Signature", color="#d0782a", edgecolor="black")
    bars = ax.bar(x, p, bottom=d + s, label="Public key", color="#2a6fb0", edgecolor="black")
    for b, tot in zip(bars, d + s + p):
        ax.annotate(f"{tot:,} B", (b.get_x() + b.get_width() / 2, tot), ha="center",
                    va="bottom", fontsize=9, xytext=(0, 2), textcoords="offset points")
    finish(fig, ax, "graph6_transmitted_bytes.png",
           "Graph 6: Total transmitted bytes = document + signature + public key",
           "Bytes sent over sig-net (linear scale)", legend=True)

    # Graph 7 (extra) - grouped bar relative to ECDSA
    fig, ax = plt.subplots(figsize=(9, 5))
    w = 0.26
    for i, (op, name, c) in enumerate((("keygen", "Key generation", "#2e8b57"),
                                       ("sign", "Signing", "#d0782a"),
                                       ("verify", "Verification", "#2a6fb0"))):
        base = row("ecdsa", op).mean_ms
        rel = [row(a, op).mean_ms / base for a in ALG_ORDER]
        annotate(ax, ax.bar(x + (i - 1) * w, rel, w, label=name, color=c, edgecolor="black"),
                 "{:.2f}")
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1)
    finish(fig, ax, "graph7_relative_to_ecdsa.png",
           "Graph 7: Time relative to ECDSA (ECDSA = 1)",
           "Relative time (x ECDSA, log scale)", log=True, legend=True)


if __name__ == "__main__":
    main()
