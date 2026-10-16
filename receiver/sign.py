"""sign.py <alg> - sign the UID document (Part E).

(1) create outbox/document.txt from the UID if it does not exist, (2) read it as bytes,
(3) load the private key, (4) sign, (5) write outbox/<alg>.sig, (6) print the signature size.
"""
import os
import sys

import oqs
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives.serialization import load_der_private_key

from common import (ALGS, check_alg, document_path, document_text, private_key_path,
                    read_bytes, signature_path, timed_ms, write_bytes)


def load_private(alg, sk_bytes):
    """Classical: cryptography key object. PQ: liboqs signer holding the secret key."""
    if ALGS[alg]["family"] == "classical":
        return load_der_private_key(sk_bytes, password=None)
    return oqs.Signature(ALGS[alg]["oqs_name"], sk_bytes)


def sign_data(alg, key, data):
    if alg == "ecdsa":
        # SHA-256 with ECDSA, DER-encoded signature
        return key.sign(data, ec.ECDSA(hashes.SHA256()))
    if alg == "rsapss":
        # PSS, MGF1(SHA-256), salt length = SHA-256 digest length (32), hash SHA-256
        return key.sign(data,
                        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                    salt_length=ALGS["rsapss"]["salt_length"]),
                        hashes.SHA256())
    # ML-DSA / SLH-DSA: sign the whole document directly (no manual hashing)
    return key.sign(data)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 sign.py <ecdsa|rsapss|mldsa|slhdsa>")
    alg = check_alg(sys.argv[1])

    doc = document_path()
    if not os.path.exists(doc):
        write_bytes(doc, document_text().encode())
        print(f"[sign] created {doc}")
    data = read_bytes(doc)

    key = load_private(alg, read_bytes(private_key_path(alg)))
    sig, ms = timed_ms(sign_data, alg, key, data)
    write_bytes(signature_path(alg), sig)

    print(f"[sign] algorithm     : {alg}")
    print(f"[sign] document      : {doc} ({len(data)} bytes)")
    print(f"[sign] signature     : {signature_path(alg)} ({len(sig)} bytes)")
    print(f"[sign] signing time  : {ms:.3f} ms")


if __name__ == "__main__":
    main()
