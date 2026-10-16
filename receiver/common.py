"""common.py - shared helpers for the digital-signature lab (sender and receiver).

Contents (Step D2):
  * STUDENT_UID read from the environment (must be exactly 10 digits)
  * ALGS: lab name -> library name / parameters
  * document text, ECDSA private scalar, benchmark message, tamper index (Section 5)
  * file-path helpers and a millisecond timing helper
"""
import hashlib
import os
import random
import sys
import time

# ---------------------------------------------------------------- UID
def get_uid():
    uid = os.environ.get("STUDENT_UID", "").strip()
    if not uid:
        sys.exit("ERROR: environment variable STUDENT_UID is not set "
                 "(start the container with -e STUDENT_UID=<your 10-digit UID>)")
    if not (uid.isdigit() and len(uid) == 10):
        sys.exit(f"ERROR: STUDENT_UID must be exactly 10 digits, got {uid!r}")
    return uid


UID = get_uid()

# ---------------------------------------------------------------- algorithms
# Strings for the PQ schemes are the exact names printed by Step D1 on this system.
ALGS = {
    "ecdsa":  {"family": "classical", "label": "ECDSA",   "curve": "SECP256R1", "hash": "SHA256"},
    "rsapss": {"family": "classical", "label": "RSA-PSS", "key_size": 3072, "e": 65537,
               "hash": "SHA256", "salt_length": 32},
    "mldsa":  {"family": "pq", "label": "ML-DSA",  "oqs_name": "ML-DSA-44"},
    "slhdsa": {"family": "pq", "label": "SLH-DSA", "oqs_name": "SLH_DSA_PURE_SHA2_128S"},
}
ALG_ORDER = ["ecdsa", "rsapss", "mldsa", "slhdsa"]


def check_alg(alg):
    if alg not in ALGS:
        sys.exit(f"ERROR: unknown algorithm {alg!r}; choose one of: {', '.join(ALG_ORDER)}")
    return alg


# ---------------------------------------------------------------- UID-derived values (Section 5)
# Order n of the P-256 group
P256_N = int("FFFFFFFF00000000FFFFFFFFFFFFFFFF"
             "BCE6FAADA7179E84F3B9CAC2FC632551", 16)


def document_text(uid=UID):
    """Line 1: Transfer Rs.<A> to Account <last 4 digits of UID>, A = 1000 + (UID mod 9000)
       Line 2: Issued by UID: <UID>"""
    amount = 1000 + (int(uid) % 9000)
    return f"Transfer Rs.{amount} to Account {uid[-4:]}\nIssued by UID: {uid}\n"


def ecdsa_private_scalar(uid=UID):
    """d = ( int( SHA-256( UID || "CNS-DSIG-ECDSA-KEY" ) ) mod (n - 1) ) + 1"""
    digest = hashlib.sha256((uid + "CNS-DSIG-ECDSA-KEY").encode()).digest()
    return (int.from_bytes(digest, "big") % (P256_N - 1)) + 1


def bench_message(uid=UID):
    """1024 bytes produced by random.Random(int(UID)).randbytes(1024)"""
    return random.Random(int(uid)).randbytes(1024)


def tamper_index(length, uid=UID):
    """index = UID mod (length of document or signature in bytes)"""
    return int(uid) % length


# ---------------------------------------------------------------- file paths
KEYS_DIR, OUTBOX_DIR, INBOX_DIR = "keys", "outbox", "inbox"


def private_key_path(alg):
    return os.path.join(KEYS_DIR, f"{alg}_private.key")


def public_key_path(alg, folder=OUTBOX_DIR):
    return os.path.join(folder, f"{alg}_public.key")


def signature_path(alg, folder=OUTBOX_DIR):
    return os.path.join(folder, f"{alg}.sig")


def document_path(folder=OUTBOX_DIR):
    return os.path.join(folder, "document.txt")


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


# ---------------------------------------------------------------- timing helper
def timed_ms(func, *args, **kwargs):
    """Run func once; return (result, elapsed milliseconds) measured with perf_counter_ns."""
    t0 = time.perf_counter_ns()
    result = func(*args, **kwargs)
    t1 = time.perf_counter_ns()
    return result, (t1 - t0) / 1e6
