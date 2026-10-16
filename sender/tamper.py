"""tamper.py <doc|sig> <file> - Mallory modifies one character/bit (Part H).

index = UID mod (file length); the byte at that index is XORed with 0x01 (exactly one bit,
hence exactly one character, changes). The result is saved as <file>.tampered; the original
file is never overwritten.
"""
import sys

from common import read_bytes, tamper_index, write_bytes


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("doc", "sig"):
        sys.exit("usage: python3 tamper.py <doc|sig> <file>")
    kind, path = sys.argv[1], sys.argv[2]
    data = bytearray(read_bytes(path))
    idx = tamper_index(len(data))
    old = data[idx]
    data[idx] ^= 0x01
    out = path + ".tampered"
    write_bytes(out, bytes(data))

    print(f"[tamper] file      : {path} ({len(data)} bytes)")
    print(f"[tamper] index     : UID mod {len(data)} = {idx}")
    print(f"[tamper] byte      : 0x{old:02x} -> 0x{data[idx]:02x} (bit 0 flipped)")
    if kind == "doc":
        print(f"[tamper] character : {chr(old)!r} -> {chr(data[idx])!r}")
        print("[tamper] original text:")
        print(read_bytes(path).decode(errors="replace"), end="")
        print("[tamper] modified text:")
        print(bytes(data).decode(errors="replace"), end="")
    print(f"[tamper] written   : {out}")


if __name__ == "__main__":
    main()
