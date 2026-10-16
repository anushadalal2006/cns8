"""bench.py [output.csv] - benchmark key generation, signing and verification (Part I).

Only the cryptographic call is inside the timed region (no Docker start-up, file I/O or
network). Per algorithm and operation: 5 un-recorded warm-up runs, then key generation x20,
signing x100, verification x100, each call timed individually with time.perf_counter_ns().
The message is the 1024-byte UID-seeded message from Section 5.
"""
import csv
import platform
import socket
import statistics
import sys
import time

from common import ALG_ORDER, ALGS, UID, bench_message
from keygen import generate
from sign import load_private, sign_data
from verify import load_public, verify_data

WARMUP = 5
RUNS = {"keygen": 20, "sign": 100, "verify": 100}


def measure(func, runs):
    for _ in range(WARMUP):                       # warm-up, not recorded
        func()
    times, result = [], None
    for _ in range(runs):
        t0 = time.perf_counter_ns()
        result = func()
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e6)             # ns -> ms
    return times, result


def stats(times):
    return {"mean_ms": statistics.mean(times), "std_ms": statistics.stdev(times),
            "min_ms": min(times), "max_ms": max(times)}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "results.csv"
    msg = bench_message()
    assert len(msg) == 1024
    print(f"[bench] UID={UID} host={socket.gethostname()} python={platform.python_version()}")
    print(f"[bench] message: 1024 bytes, sha256-prefix={__import__('hashlib').sha256(msg).hexdigest()[:16]}")

    rows = []
    for alg in ALG_ORDER:
        # key generation (the key pair produced last is used for signing/verification)
        kg_times, (sk, pk) = measure(lambda: generate(alg), RUNS["keygen"])
        priv, pub = load_private(alg, sk), load_public(alg, pk)

        sg_times, sig = measure(lambda: sign_data(alg, priv, msg), RUNS["sign"])
        vf_times, ok = measure(lambda: verify_data(alg, pub, msg, sig), RUNS["verify"])

        # the signature from the last signing loop must verify, otherwise we timed failures
        if not (ok and verify_data(alg, pub, msg, sig)):
            sys.exit(f"ERROR: {alg} signature from the benchmark did not verify")

        for op, times in (("keygen", kg_times), ("sign", sg_times), ("verify", vf_times)):
            s = stats(times)
            rows.append({"uid": UID, "algorithm": alg, "operation": op, "runs": len(times),
                         **{k: f"{v:.4f}" for k, v in s.items()},
                         "public_key_bytes": len(pk), "private_key_bytes": len(sk),
                         "signature_bytes": len(sig)})
            print(f"[bench] {alg:7s} {op:7s} runs={len(times):3d} mean={s['mean_ms']:10.4f} ms "
                  f"std={s['std_ms']:9.4f} min={s['min_ms']:10.4f} max={s['max_ms']:10.4f}")
        print(f"[bench] {alg:7s} sizes: pk={len(pk)} B  sk={len(sk)} B  sig={len(sig)} B  "
              f"verify-check=PASS")

    fields = ["uid", "algorithm", "operation", "runs", "mean_ms", "std_ms", "min_ms", "max_ms",
              "public_key_bytes", "private_key_bytes", "signature_bytes"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"[bench] written {out}")


if __name__ == "__main__":
    main()
