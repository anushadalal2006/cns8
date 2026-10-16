"""keygen.py <alg> [--independent] - generate the key pair of the chosen algorithm (Step D3).

--independent (wrong-key test, Part H Test 4 only): the ECDSA key comes from the secure random
generator instead of the UID. Without it, the receiver would re-derive the sender's exact ECDSA
key from the same STUDENT_UID, and the "wrong" key would really be the right one.

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


def generate(alg, independent=False):
    """Return (private_key_bytes, public_key_bytes) for alg."""
    if alg == "ecdsa" and independent:
        return _der_pair(ec.generate_private_key(ec.SECP256R1()))
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
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--independent"):
        sys.exit("usage: python3 keygen.py <ecdsa|rsapss|mldsa|slhdsa> [--independent]")
    alg = check_alg(sys.argv[1])
    independent = len(sys.argv) == 3
    (sk, pk), ms = timed_ms(generate, alg, independent)
    write_bytes(private_key_path(alg), sk)
    write_bytes(public_key_path(alg), pk)
    name = ALGS[alg].get("oqs_name", ALGS[alg]["label"])
    print(f"[keygen] algorithm      : {alg} ({name})"
          + ("  [independent key from the secure RNG]" if independent and alg == "ecdsa" else ""))
    print(f"[keygen] private key    : {private_key_path(alg):28s} {len(sk):6d} bytes")
    print(f"[keygen] public key     : {public_key_path(alg):28s} {len(pk):6d} bytes")
    print(f"[keygen] generation time: {ms:.3f} ms")


if __name__ == "__main__":
    main()
