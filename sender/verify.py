"""verify.py <alg> [document] [public_key] [signature] - verify a signature (Part G).

Defaults: inbox/document.txt, inbox/<alg>_public.key, inbox/<alg>.sig
Uses exactly the same parameters as sign.py; prints PASS or FAIL and the verification time.
"""
import sys

import oqs
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives.serialization import load_der_public_key

from common import (ALGS, INBOX_DIR, check_alg, document_path, public_key_path,
                    read_bytes, signature_path, timed_ms)


def load_public(alg, pk_bytes):
    """Classical: cryptography public-key object. PQ: (liboqs verifier, raw public key)."""
    if ALGS[alg]["family"] == "classical":
        return load_der_public_key(pk_bytes)
    return oqs.Signature(ALGS[alg]["oqs_name"]), pk_bytes


def verify_data(alg, key, data, sig):
    """Return True if the signature is valid, False otherwise."""
    if ALGS[alg]["family"] == "classical":
        try:
            if alg == "ecdsa":
                key.verify(sig, data, ec.ECDSA(hashes.SHA256()))
            else:
                key.verify(sig, data,
                           padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                       salt_length=ALGS["rsapss"]["salt_length"]),
                           hashes.SHA256())
            return True
        except InvalidSignature:          # cryptography raises on failure
            return False
    verifier, pk = key
    return verifier.verify(data, sig, pk)  # liboqs returns a boolean


def main():
    if not 2 <= len(sys.argv) <= 5:
        sys.exit("usage: python3 verify.py <alg> [document] [public_key] [signature]")
    alg = check_alg(sys.argv[1])
    doc = sys.argv[2] if len(sys.argv) > 2 else document_path(INBOX_DIR)
    pub = sys.argv[3] if len(sys.argv) > 3 else public_key_path(alg, INBOX_DIR)
    sig_file = sys.argv[4] if len(sys.argv) > 4 else signature_path(alg, INBOX_DIR)

    data, sig = read_bytes(doc), read_bytes(sig_file)
    try:
        key = load_public(alg, read_bytes(pub))
        ok, ms = timed_ms(verify_data, alg, key, data, sig)
    except ValueError as exc:             # e.g. malformed key / wrong key length
        ok, ms = False, 0.0
        print(f"[verify] error: {exc}")

    print(f"[verify] algorithm : {alg}")
    print(f"[verify] document  : {doc}")
    print(f"[verify] public key: {pub}")
    print(f"[verify] signature : {sig_file}")
    print(f"[verify] time      : {ms:.3f} ms")
    print(f"[verify] RESULT    : {'PASS (VALID)' if ok else 'FAIL (INVALID)'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
