"""keygen.py <alg> - generate the key pair of the chosen algorithm (Step D3).

Private key -> keys/<alg>_private.key   (never leaves the container)
Public key  -> outbox/<alg>_public.key
"""
import sys

import oqs
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from common import (ALGS, check_alg, ecdsa_private_scalar, private_key_path,
                    public_key_path, timed_ms, write_bytes)


def _der_pair(private_key):
    sk = private_key.private_bytes(encoding=serialization.Encoding.DER,
                                   format=serialization.PrivateFormat.PKCS8,
                                   encryption_algorithm=serialization.NoEncryption())
    pk = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    return sk, pk


def generate(alg):
    """Return (private_key_bytes, public_key_bytes) for alg."""
    if alg == "ecdsa":
        # private key built from the UID-derived scalar d on curve P-256
        return _der_pair(ec.derive_private_key(ecdsa_private_scalar(), ec.SECP256R1()))
    if alg == "rsapss":
        p = ALGS["rsapss"]
        return _der_pair(rsa.generate_private_key(public_exponent=p["e"], key_size=p["key_size"]))
    # ML-DSA / SLH-DSA: raw public key and raw secret key from liboqs
    with oqs.Signature(ALGS[alg]["oqs_name"]) as signer:
        pk = signer.generate_keypair()
        sk = signer.export_secret_key()
    return sk, pk


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 keygen.py <ecdsa|rsapss|mldsa|slhdsa>")
    alg = check_alg(sys.argv[1])
    (sk, pk), ms = timed_ms(generate, alg)
    write_bytes(private_key_path(alg), sk)
    write_bytes(public_key_path(alg), pk)
    name = ALGS[alg].get("oqs_name", ALGS[alg]["label"])
    print(f"[keygen] algorithm      : {alg} ({name})")
    print(f"[keygen] private key    : {private_key_path(alg):28s} {len(sk):6d} bytes")
    print(f"[keygen] public key     : {public_key_path(alg):28s} {len(pk):6d} bytes")
    print(f"[keygen] generation time: {ms:.3f} ms")


if __name__ == "__main__":
    main()
