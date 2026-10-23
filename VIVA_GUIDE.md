# Experiment 8 — Viva Guide (from the ground up)

**Anusha Dalal · UID 2024300032**

How to use this guide:

- **Part 0** is the 2-minute story of what you did. Learn it first; open your viva with it.
- **Part 1** teaches the theory from zero. Every later answer builds on it.
- **Part 2** walks through the experiment step by step with *your* outputs.
- **Part 3** explains every program line by line (line numbers match the files in `sender/`).
- **Part 4** explains every number in your results, including the strange-looking ones.
- **Part 5** is a bank of twisted viva questions with answers.
- **Part 6** is a one-page cheat sheet of numbers to memorise.

---

# Part 0 — The 2-minute story

> "I implemented the full digital-signature workflow between two Docker containers, a **sender** (Alice) and a **receiver** (Bob), on a user-defined bridge network called **sig-net**. I used two classical algorithms, **RSA-PSS (3072-bit)** and **ECDSA (P-256)**, and two NIST post-quantum standards from 2024, **ML-DSA-44** (lattice-based, FIPS 204) and **SLH-DSA-SHA2-128s** (hash-based, FIPS 205).
>
> The sender generated key pairs, created a document from my UID ('Transfer Rs.3032 to Account 0032 / Issued by UID: 2024300032'), signed it with all four algorithms and served only the **public** files over HTTP. The receiver downloaded them with curl by container name and verified all four: **PASS**.
>
> Then I tampered: changing one character of the document, one bit of a signature, or using a wrong public key made all four **FAIL**.
>
> Finally I benchmarked key generation, signing and verification (5 warm-ups, then 20/100/100 timed runs, 3 runs, median kept) and compared sizes. ECDSA is the most compact (221 bytes transmitted). ML-DSA is about as fast as ECDSA but transmits 3,791 bytes. SLH-DSA has a tiny 32-byte public key but a 7,856-byte signature and ~471 ms signing. The post-quantum schemes cost size (and for SLH-DSA, speed), but they survive Shor's algorithm, which breaks RSA and ECDSA."

---

# Part 1 — Theory from the ground up

## 1.1 What security goals exist, and which ones a signature gives

| Goal | Meaning | Does a digital signature give it? |
|---|---|---|
| **Confidentiality** | Only intended people can *read* the data | **No.** Our document travelled in plain text over HTTP. Signatures do not hide anything. |
| **Integrity** | Data was not *changed* | **Yes.** Any change makes verification fail (your Tests 2 and 3). |
| **Authentication** (of origin) | Data really came from the claimed sender | **Yes**, *provided* you trust that the public key belongs to the sender (see PKI, §1.12). |
| **Non-repudiation** | The sender cannot later deny having signed | **Yes.** Only the private-key holder could have produced the signature. A MAC cannot give this. |

> Twisted trap: "Your experiment provides confidentiality?" — **No.** Nothing was encrypted. Anyone on sig-net could read `document.txt`.

## 1.2 Hash functions (the foundation of everything)

A **cryptographic hash function** H takes input of any length and outputs a fixed-length **digest**. SHA-256 outputs 256 bits = 32 bytes.

Required properties:

1. **Pre-image resistance** — given h, you cannot find M with H(M) = h.
2. **Second pre-image resistance** — given M, you cannot find a different M′ with H(M′) = H(M).
3. **Collision resistance** — you cannot find *any* pair M ≠ M′ with H(M) = H(M′).
4. **Avalanche effect** — changing one input bit changes about half of the output bits, unpredictably.

Why signatures hash first ("**hash-and-sign**"):

- RSA/ECDSA can only sign a number smaller than the modulus/group order. Hashing turns any-length document into a fixed 256-bit value.
- It is much faster to sign 32 bytes than a whole file.
- Security now depends on the hash too: if an attacker finds a **collision** (M, M′ with the same hash), a signature on M is also valid for M′. That is why we use SHA-256 (no known collisions), not MD5 or SHA-1.

In your Test 2, flipping one bit of 'a' (0x61 → 0x60) changed the SHA-256 digest completely (avalanche), so the signature no longer matched.

The document's SHA-256 on both sides was `d44e70df…f7f388`. Matching hashes prove the **transfer** was not corrupted. They do **not** prove who sent it: an attacker can change the file *and* recompute the hash, because a hash has **no key**. That is exactly why we need signatures.

## 1.3 Symmetric vs asymmetric, MAC vs signature

- **Symmetric** crypto: one shared secret key (AES, HMAC). Fast, but both sides have the same key.
- **Asymmetric** (public-key) crypto: a **key pair**. The private key SK is kept secret; the public key PK can be published. They are mathematically linked, but SK cannot be computed from PK (that is the "hard problem").

| | MAC (e.g. HMAC-SHA256) | Digital signature |
|---|---|---|
| Keys | One shared secret key | Private key signs, public key verifies |
| Who can create a valid tag? | Anyone with the shared key (both parties) | Only the private-key holder |
| Who can verify? | Only key holders | Anyone with the public key |
| Non-repudiation | **No** — the receiver could have made the tag | **Yes** |
| Speed / size | Very fast, 32-byte tag | Slower, bigger |

## 1.4 The digital-signature model (your Part A diagram)

A signature scheme is **three algorithms**:

1. **KeyGen() → (PK, SK)** — uses randomness (in your experiment the ECDSA one was derived from the UID instead).
2. **Sign(SK, M) → S** — in hash-and-sign: h = H(M), then S = Sign(SK, h).
3. **Verify(PK, M, S) → ACCEPT / REJECT** — the receiver recomputes h′ = H(M′) from what it received and checks S against h′ using PK.

The flow on your diagram:

```
Alice (sender)                       insecure channel                Bob (receiver)
M ──H()──> h ──Sign(SK_A, h)──> S
send (M || S) ───────────────────────────────────────────> receives M', S
PK_A ──────────────────────────────────────────────────────> PK_A
SK_A never leaves Alice (dashed arrow)
                                                             h' = H(M')
                                                             Verify(PK_A, h', S)
                                                             ACCEPT if valid, REJECT if not
Mallory modifies M → M' in the channel  ⇒  h' ≠ h  ⇒  REJECT
```

**Correctness:** if nobody tampers, Verify always accepts an honest signature.
**Security (EUF-CMA)** — "existential unforgeability under chosen-message attack": even if the attacker can get signatures on *any messages they choose*, they cannot produce a valid signature on a *new* message. This is the standard security definition all four algorithms aim for.

`||` means **concatenation** (placing bytes one after the other).

## 1.5 RSA and RSA-PSS

### RSA key generation
1. Pick two large random primes **p** and **q** (1536 bits each for RSA-3072).
2. **n = p·q** (the 3072-bit **modulus**, public).
3. φ(n) = (p−1)(q−1).
4. Public exponent **e = 65537** (= 2¹⁶+1).
5. Private exponent **d = e⁻¹ mod φ(n)**, i.e. e·d ≡ 1 (mod φ(n)).
6. PK = (n, e), SK = (n, d) (plus p, q and CRT values to speed things up).

Security rests on **integer factorisation**: knowing n, you cannot find p and q, so you cannot compute d.

### Textbook RSA signing and why it is insecure
s = m^d mod n, verify by checking s^e mod n = m. Problems:
- **Multiplicative (malleability) attack:** sig(m₁)·sig(m₂) = sig(m₁·m₂) mod n, so an attacker can create a signature on a new message.
- **Existential forgery:** choose any s, compute m = s^e mod n; (m, s) is a valid pair.

So real RSA always uses **padding**.

### PSS (Probabilistic Signature Scheme) — what you used
- Hash the message with **SHA-256**.
- Mix in a random **salt** (you used **32 bytes** = the SHA-256 output length, as RFC 8017 recommends).
- Expand with **MGF1(SHA-256)** — a *Mask Generation Function* that stretches a hash into a mask of any length: H(seed‖0) ‖ H(seed‖1) ‖ …
- Build an encoded message ending in the trailer byte 0xBC, then compute s = EM^d mod n.

Because of the random salt, **signing the same document twice gives different signatures**, and both verify. PSS has a security proof (in the random-oracle model), which the older PKCS#1 v1.5 padding lacks.

### Why RSA verification is so much faster than signing (your ratio 39×)
- Verify raises to **e = 65537**: only 17 squarings/multiplications.
- Sign raises to **d**, a ~3072-bit number: thousands of operations (CRT makes it about 4× faster, still slow).

### Why RSA key generation is slow *and* hugely variable (your 198 ms ± 102 ms)
It must find two random 1536-bit **primes**: pick random odd numbers and test (Miller–Rabin) until one is prime. The number of tries is random, so the time varies a lot (your min 38.9 ms, max 383 ms).

### Sizes
- Signature = modulus size = 3072 bits = **384 bytes**.
- RSA-3072 ≈ **128-bit** security (same class as P-256).

## 1.6 Elliptic curves and ECDSA

### The curve
P-256 (secp256r1, "prime256v1") is the set of points (x, y) satisfying **y² = x³ − 3x + b (mod p)**, with p a 256-bit prime. Points can be "added" (a geometric rule turned into modular arithmetic), forming a **group**.

- **Generator G**: a fixed public point.
- **Order n**: the number of points generated by G (that FFFFFFFF00000000…FC632551 value in `common.py`). n·G = the point at infinity (the identity).
- **Scalar multiplication**: d·G = G + G + … + G (d times), computed quickly by double-and-add.

### Keys
- Private key: an integer **d** with **1 ≤ d ≤ n−1**.
- Public key: the point **Q = d·G**.

Security rests on the **elliptic-curve discrete logarithm problem (ECDLP)**: given Q and G, finding d is infeasible (best classical attack ~2¹²⁸ steps for P-256).

### ECDSA signing (h = SHA-256(M), as an integer)
1. Pick a fresh random **nonce k** in [1, n−1].
2. R = k·G; **r = R.x mod n** (if r = 0, pick another k).
3. **s = k⁻¹ (h + r·d) mod n** (if s = 0, pick another k).
4. Signature = **(r, s)**.

### ECDSA verification
1. Check 1 ≤ r, s ≤ n−1.
2. w = s⁻¹ mod n, u₁ = h·w, u₂ = r·w.
3. X = u₁·G + u₂·Q.
4. Accept iff **X.x mod n = r**.

Why it works: u₁G + u₂Q = (h + r·d)·s⁻¹·G = k·G = R.

### Why ECDSA verification was *slower* than signing (your 0.124 ms vs 0.044 ms)
- Signing needs **one** scalar multiplication, k·G, with a *fixed* base G, for which libraries keep precomputed tables.
- Verifying needs **two** scalar multiplications (u₁G + u₂Q), and Q is not precomputed.

### The nonce k is critical
- If k is **ever reused** for two messages, anyone can solve two equations to recover d. (Sony's PlayStation 3 was broken this way in 2010.)
- If k is even slightly biased, lattice attacks can recover d.
- Fix: use a strong random generator, or **deterministic nonces (RFC 6979)**: k derived from d and h.
- The `cryptography` library (OpenSSL) uses a random k by default. **Therefore your ECDSA signatures change every run even though d is fixed.** You can see it: between your runs `ecdsa.sig` changed but `ecdsa_public.key` did not.

### ECDSA signature encoding (DER) — your actual bytes
Your `ecdsa.sig` (71 bytes) begins:
```
30 45 | 02 20 65 4f ab 59 … (r, 32 bytes) | 02 21 00 be d4 3d … (s, 33 bytes)
```
- `30 45` = SEQUENCE of length 0x45 = 69 bytes.
- `02 20` = INTEGER of 32 bytes (that is r).
- `02 21 00 be…` = INTEGER of 33 bytes: s starts with 0xBE, whose top bit is 1, so DER adds a leading `00` to keep the integer positive.
- Total 2 + 2 + 32 + 2 + 33 = **71 bytes**. Depending on leading bits of r and s, ECDSA DER signatures are 70, 71 or 72 bytes. (Your benchmark CSV shows 72 bytes for a different signature — same reason.)

**ECDSA malleability:** if (r, s) is valid, so is (r, n−s). Not a forgery of a *new* message, but it means a signature is not a unique fingerprint of the message.

### Sizes
- Public key Q in uncompressed form: 04 ‖ x ‖ y = 65 bytes. Wrapped in SubjectPublicKeyInfo DER = **91 bytes** (see §1.11).
- Signature (r, s) = 64 bytes raw, **70–72 bytes** DER.
- Security ≈ **128 bits**.

## 1.7 The quantum threat

### Shor's algorithm (1994)
On a large **fault-tolerant** quantum computer, Shor's algorithm finds the **period** of a function in polynomial time. That solves:
- **Integer factorisation** → breaks **RSA** (find p, q from n, then d).
- **Discrete logarithms**, including elliptic-curve ones → breaks **ECDSA** (find d from Q).

Making keys bigger does **not** help: Shor is polynomial, so RSA-15360 falls almost as easily. Current estimates need on the order of a million noisy physical qubits for RSA-2048; today's machines are far smaller, but planning must start now.

### Grover's algorithm
Gives a **quadratic** speed-up for unstructured search: a 2²⁵⁶ brute-force search becomes ~2¹²⁸. Hash functions like SHA-256 therefore stay secure (just use big enough outputs). This is why **hash-based SLH-DSA** is considered very safe.

### Why a signature valid today may be dangerous in 20 years
Once a quantum computer can compute a 2026 RSA/ECDSA private key from its (public!) public key, an attacker can create **new signatures that are indistinguishable from genuine old ones**. Anything that must stay trustworthy for decades — firmware, root certificates, land/legal records, archived contracts — can no longer be trusted. So long-lived signatures need PQ algorithms now.

(Contrast "**harvest now, decrypt later**", which is about *encryption*: an attacker records encrypted traffic today and decrypts it later. For *signatures* the risk is **forgery later**.)

### NIST's response (August 2024)
- **FIPS 203 — ML-KEM** (key exchange/encryption, from CRYSTALS-Kyber) — *not* a signature.
- **FIPS 204 — ML-DSA** (signatures, from CRYSTALS-Dilithium) — lattices.
- **FIPS 205 — SLH-DSA** (signatures, from SPHINCS+) — hash functions only.

## 1.8 ML-DSA (Module-Lattice Digital Signature Algorithm)

### The hard problems (intuition)
- **Learning With Errors (LWE):** given A and t = A·s + e (mod q), where s and e are *small* secret vectors, find s. Without the small noise e it is just linear algebra; the noise makes it hard, even for quantum computers.
- **Short Integer Solution (SIS):** find a *short* non-zero vector z with A·z = 0 (mod q).
- **"Module"** means the entries are polynomials in a ring (mod X²⁵⁶+1, q = 8380417), not plain numbers. This gives a good balance of size and speed.

### Keys
- Public: a seed ρ (expanded into matrix A) and **t = A·s₁ + s₂** (high bits t₁ published).
- Secret: the small vectors s₁, s₂ (plus seeds/hashes).

### Signing — "Fiat–Shamir with aborts"
1. Pick a random masking vector y.
2. w = A·y; take its high bits w₁.
3. Challenge **c = H(μ ‖ w₁)** where μ is a hash of the message and public key.
4. **z = y + c·s₁**.
5. If z (or related values) would **leak information about s₁** (too large), **reject and restart** from step 1. This is **rejection sampling**.
6. Signature = (c̃, z, hint).

**Verification** recomputes w₁ from A·z − c·t and checks that H(μ ‖ w₁) gives the same challenge and that z is short.

### Why your ML-DSA signing time had a large standard deviation (0.066 ± 0.034 ms)
Rejection sampling: each signature needs a *random number* of attempts (on average about 4 for ML-DSA-44). Verification has no loop, so it is fast and steady (0.024 ± 0.002 ms).

### Why ML-DSA is fast
Polynomial multiplication uses the **Number Theoretic Transform (NTT)**, a fast-Fourier-like trick, and all numbers fit in 32 bits.

### Sizes (ML-DSA-44, NIST security category 2)
- Public key **1312 B** = ρ (32 B) + t₁ (4 polynomials × 256 coefficients × 10 bits = 1280 B).
- Private key **2560 B**.
- Signature **2420 B** = c̃ (32 B) + z (4 × 256 × 18 bits = 2304 B) + hint (84 B).

ML-DSA signs the **whole message** (it hashes internally), which is why `sign.py` passes the document directly to it.

## 1.9 SLH-DSA (Stateless Hash-Based Digital Signature Algorithm)

Security relies **only on the hash function** (here SHA-256). No number theory, no lattices, so it is the most conservative choice.

Build it up in steps:

### Step 1 — Lamport one-time signature (the idea)
- Secret key: 256 pairs of random values. Public key: their hashes.
- To sign a 256-bit digest, reveal one value from each pair (the one matching each bit).
- Verifier hashes the revealed values and compares with the public key.
- **One-time only**: signing a second message reveals more secrets and allows forgeries.

### Step 2 — WOTS+ (Winternitz one-time signature)
Shrinks Lamport by using **hash chains**: apply H repeatedly; a chunk value v is signed by revealing the chain position v; the verifier hashes forward to the end. Still one-time.

### Step 3 — Merkle tree (many one-time keys, one public key)
Put many WOTS+ public keys as **leaves** of a binary hash tree. The **root** is the public key. A signature = one WOTS+ signature + the **authentication path** (sibling hashes up to the root).

### Step 4 — Hypertree + FORS (stateless)
- A **hypertree**: trees of trees (d = 7 layers for 128s), so the total number of leaves is astronomically large (2⁶³).
- The leaf is chosen **pseudo-randomly from the message**, so the signer never needs to remember which keys were used. That is what **stateless** means.
- At the bottom, a **FORS** ("Forest Of Random Subsets") **few-time** signature signs the message digest; it stays secure even if a leaf is (rarely) reused.

**Stateful** alternatives (XMSS, LMS) are smaller and faster but the signer must store a counter; reusing a one-time key (e.g. after restoring a backup) is catastrophic. SLH-DSA avoids that.

### Your signature size, worked out (SLH-DSA-SHA2-128s: n = 16, h = 63, d = 7, k = 14, a = 12, len = 35)
- randomiser R: n = 16 B
- FORS: k·(a+1)·n = 14 × 13 × 16 = 2912 B
- hypertree: (h + d·len)·n = (63 + 7 × 35) × 16 = 4928 B
- Total = 16 + 2912 + 4928 = **7856 B** ✔

### Keys
- Public key **32 B** = PK.seed (16 B) + PK.root (16 B).
- Private key **64 B** = SK.seed + SK.prf + PK.seed + PK.root.

### Why signing is so slow (your 471 ms)
Each signature recomputes, from the secret seed, a FORS forest and one WOTS+ signature plus Merkle path for each of the 7 layers: hundreds of thousands of SHA-256 calls. Verification only recomputes one path per layer (a few thousand hashes), so it is fast (0.406 ms). Key generation (55.6 ms) builds the top-layer tree to get the root.

### "s" vs "f", "pure" vs "prehash"
- **s = small** signatures (taller trees, slower signing). **f = fast** signing, bigger signatures (~17 KB for 128f).
- **PURE**: the algorithm processes the message itself (what you used). **PREHASH** variants sign a pre-computed hash of the message.

## 1.10 Security levels — is the comparison fair?

| Algorithm | Security |
|---|---|
| RSA-3072 | ~128-bit classical |
| ECDSA P-256 | ~128-bit classical |
| ML-DSA-44 | NIST category 2 (≈ SHA-256 collision search) |
| SLH-DSA-SHA2-128s | NIST category 1 (≈ AES-128 key search) |

All are in the **~128-bit class**, so the comparison is fair (the lab sheet chose them for this). The classical two give **0 bits** against a large quantum computer.

## 1.11 Encodings: ASN.1, DER, PKCS#8, SubjectPublicKeyInfo, PEM, raw

- **ASN.1** is a language describing data structures; **DER** is its exact binary encoding (Tag–Length–Value).
- **SubjectPublicKeyInfo (SPKI)**: standard wrapper for a public key = algorithm identifier + key bits.
- **PKCS#8**: standard wrapper for a private key.
- **PEM** = DER encoded in **Base64** with `-----BEGIN …-----` lines. About 4/3 larger plus headers. (This is why someone's PEM ECDSA key is 178/241 B while your DER key is 91/138 B — *same key, different encoding*.)
- **Raw**: liboqs keys are plain byte strings with no wrapper, so their sizes equal the standards' values exactly.

Your ECDSA public key (91 B), decoded:
```
30 59                                   SEQUENCE (89 bytes)
  30 13                                 SEQUENCE (algorithm identifier)
    06 07 2a 86 48 ce 3d 02 01          OID 1.2.840.10045.2.1   = id-ecPublicKey
    06 08 2a 86 48 ce 3d 03 01 07       OID 1.2.840.10045.3.1.7 = prime256v1 (P-256)
  03 42 00                              BIT STRING (66 bytes, 0 unused bits)
    04 5e 7e a1 9b …                    04 = uncompressed point, then x (32 B), y (32 B)
```

Your ECDSA private key (PKCS#8, 138 B) contains `04 20 32 25 47 48 …`: an OCTET STRING of 32 bytes = **your UID-derived d = 0x32254748…**.

Your RSA public key (422 B) = SEQUENCE → algorithm OID rsaEncryption → BIT STRING → SEQUENCE { INTEGER n (385 bytes: a leading 00 + 384 bytes), INTEGER e = `01 00 01` = 65537 }.

## 1.12 PKI and the man-in-the-middle problem

Verification proves only "this signature matches **this public key**". It does not prove *whose* key it is.

**Attack:** Mallory intercepts the download and substitutes her own document, signature *and* public key. Bob verifies → **PASS**. In your lab the public key came over the same untrusted HTTP channel, so this attack would work.

**Fix — Public Key Infrastructure:**
- A **Certificate Authority (CA)** signs a **certificate** (X.509) binding a public key to an identity ("this PK belongs to Alice").
- Bob already trusts a few **root CA** keys (pre-installed in the OS/browser trust store).
- Bob checks the **chain** of signatures up to a trusted root, plus validity dates and **revocation** (CRL/OCSP).
- Alternatives: comparing a key **fingerprint** over a separate trusted channel, or **key pinning**.

## 1.13 Hybrid signatures

Sign with **both** a classical and a PQ algorithm; accept only if **both** verify. Secure as long as **at least one** is unbroken. Protects against:
- undiscovered weaknesses in new PQ schemes (Rainbow and SIKE were broken during the NIST process);
- quantum attacks on the classical scheme.

Cost: the sizes add up (ECDSA + ML-DSA = 71 + 2420 = 2491 B per signature).

## 1.14 Docker fundamentals

- **Image** = a read-only template built in **layers** from a Dockerfile (each instruction = a layer, cached).
- **Container** = a running instance of an image, with its own writable layer.
- Containers are **not VMs**. They share the **host kernel**. Isolation comes from Linux **namespaces** (separate process tree, network stack, filesystem view, hostname) and **cgroups** (CPU/memory limits). That is why CPU-bound crypto runs at native speed inside them.
- On your Windows laptop, Docker runs inside **WSL2**, a lightweight Linux VM; the containers share *that* Linux kernel (`6.6.87.2-microsoft-standard-WSL2`).

**Networking**
- `docker network create sig-net` creates a **user-defined bridge**: a virtual switch on the host. Docker gave it subnet **172.18.0.0/16**, gateway **172.18.0.1** (the host side). Sender got **172.18.0.2**, receiver **172.18.0.3**.
- A user-defined bridge has an **embedded DNS server (127.0.0.11)**, so containers find each other **by name** (`ping receiver`, `curl http://sender:8000`). The **default** bridge network does **not** provide name resolution.
- Containers on the same network can reach **all** of each other's ports. `-p` (publish) is only needed to expose a port to the **host** or outside world, which is why we never used `-p 8000:8000`.

**Storage**
- `-v ~/sig-lab/sender:/lab` is a **bind mount**: the host folder appears inside the container at `/lab`. Files survive even if the container is deleted, and you can see them on the host.
- (A *named volume* would be managed by Docker instead; we did not use one.)

## 1.15 Benchmarking methodology

- **`time.perf_counter_ns()`**: a monotonic, high-resolution clock in integer nanoseconds. Not affected by system clock changes (unlike `time.time()`), and integers avoid floating-point rounding for tiny durations.
- **Warm-up runs** (5): the first calls are slow because of lazy initialisation inside the libraries, cold CPU caches and branch predictors, page faults, and CPU frequency ramp-up. They are excluded.
- **Many repetitions** (20/100/100): one measurement is noise; the **mean** gives the typical cost, the **standard deviation** the spread, **min** the best case (least disturbed), **max** shows outliers (interruptions).
- **3 whole runs, median kept**: protects against one run being disturbed (e.g. by a background task).
- **Only the crypto call is timed**: no file I/O, network, or Docker start-up inside the timed region.

---

# Part 2 — The experiment, step by step, with your outputs

### Part A — Hand-drawn diagram
The model of §1.4 with 8 required elements: parties + channel; M, H, h; SK_A (dashed) and PK_A; S = Sign(SK_A, h) and (M‖S); PK_A to receiver, SK_A never sent; h′ = H(M′) and Verify; ACCEPT/REJECT box; Mallory changing M → M′ ⇒ REJECT.

### Step C3–C4 — Build the image
`docker build -t sig-lab:1.0 .` built one image (1.23 GB) from the lab's Dockerfile: Ubuntu 24.04 + Python + `cryptography` + `liboqs-python`. The final `RUN python3 -c "import oqs…"` makes liboqs-python download and compile the C library **liboqs** during the build, so the containers start ready. (Line-by-line in §3.1.)

### Step C5 — Network
`docker network create sig-net` → `docker network ls` shows driver **bridge** → `docker network inspect sig-net` shows subnet 172.18.0.0/16, gateway 172.18.0.1, and no containers yet.

### Step C6 — Containers
```
docker run -dit --name sender   --hostname sender   --network sig-net -e STUDENT_UID=2024300032 -v ~/sig-lab/sender:/lab   sig-lab:1.0
docker run -dit --name receiver --hostname receiver --network sig-net -e STUDENT_UID=2024300032 -v ~/sig-lab/receiver:/lab sig-lab:1.0
```
- `-d` detached (background), `-i` keep STDIN open, `-t` allocate a terminal.
- `--name` = Docker's name for the container *and* its DNS name on sig-net; `--hostname` = the name the container sees for itself (your prompt `root@sender`).
- `-e STUDENT_UID=…` sets the environment variable that `common.py` reads.
- `docker ps` showed both **Up** with command `"sleep infinity"`.

### Step C7 — Connectivity
- `docker network inspect sig-net` now lists receiver 172.18.0.3/16 and sender 172.18.0.2/16 with their MAC addresses.
- `ping -c 3 receiver` from the sender: **3 sent, 3 received, 0% loss**. `receiver.sig-net (172.18.0.3)` shows DNS by name worked. **ttl=64** means no router in between (same bridge). The first ping (1.85 ms) is slower than the others (~0.1 ms) because of ARP address resolution and cold caches.
- `echo $STUDENT_UID` printed 2024300032 inside the container.

### Step C8 — Environment (Table 1)
i5-1235U, 12 logical CPUs, 3.7 GiB RAM (memory WSL gives Linux), Ubuntu 24.04.5 on WSL2 kernel 6.6.87.2, Docker 29.8.2, cryptography 50.0.2, liboqs 0.16.0. Recorded because timings depend on hardware.

### Step D1 — Algorithm names
Listed liboqs mechanisms containing 'ML-DSA' or 'SLH': the exact strings **ML-DSA-44** and **SLH_DSA_PURE_SHA2_128S** were then used in `common.py`.

### Step D3 — Key generation (single runs)
| | private | public | time (first call) |
|---|---|---|---|
| ECDSA | 138 B | 91 B | 11.2 ms |
| RSA-PSS | 1792 B | 422 B | 461.6 ms |
| ML-DSA | 2560 B | 1312 B | 8.2 ms |
| SLH-DSA | 64 B | 32 B | 105.5 ms |

Private keys went to `keys/`, public keys to `outbox/`.

### Part E — Signing
`sign.py` created `outbox/document.txt` (59 bytes):
```
Transfer Rs.3032 to Account 0032
Issued by UID: 2024300032
```
(A = 1000 + 2024300032 mod 9000 = 1000 + 2032 = **3032**; last 4 digits **0032**.)
Signatures: ECDSA 71 B, RSA 384 B, ML-DSA 2420 B, SLH-DSA 7856 B (SLH-DSA took 559 ms). SHA-256 of the document: `d44e70df…7cf7f388`.

### Part F — Transfer
- Sender: `cd /lab/outbox && python3 -m http.server 8000` serves the `outbox/` folder.
- Receiver: `curl -O http://sender:8000/document.txt`, then a loop downloading `<alg>.sig` and `<alg>_public.key`.
- The server log shows **9 GET requests, all `200`, all from 172.18.0.3** (the receiver).
- The receiver's SHA-256 matched the sender's ⇒ the file arrived unchanged.
- **Only public data was in outbox/.** keys/ was never served.

### Part G — Verification
All four printed **PASS (VALID)**. Sizes from `stat -c %s` built Table 2: transmitted = doc + sig + public key = 221 / 865 / 3791 / 7947 bytes.

### Part H — Tampering
| Test | What changed | Result |
|---|---|---|
| 1 | nothing | PASS × 4 |
| 2 | document byte 2 (UID mod 59 = 2): 'a' 0x61 → '`' 0x60 → "Tr\`nsfer…" | FAIL × 4 |
| 3 | one bit of each signature at UID mod length: ECDSA byte 4 (0x65→0x64), RSA byte 256 (0x19→0x18), ML-DSA byte 1492 (0x78→0x79), SLH-DSA byte 5232 (0xf9→0xf8) | FAIL × 4 |
| 4 | receiver's own key pair (ECDSA: independent random key) | FAIL × 4 |

`cmp` confirmed all four receiver public keys differ from the sender's.

### Part I — Benchmark
`bench.py` ran 3 times on the sender (results_run1/2/3.csv), sums of mean times 813.49 / 666.12 / **727.24** ms → median = **run 3**, copied to `results.csv`. Then once on the receiver.

### Section 15 — Graphs
`plot.py` read `results.csv` and drew 7 PNGs; `docker cp sender:/lab/graphs ./graphs` copied them to the host.

---

# Part 3 — The code, line by line

## 3.1 Dockerfile

| Line | Code | What and why |
|---|---|---|
| 1 | `FROM ubuntu:24.04` | Base image: Ubuntu 24.04 LTS. Every later instruction adds a layer on top. |
| 2 | `ENV DEBIAN_FRONTEND=noninteractive` | Stops apt from asking interactive questions (e.g. timezone for tzdata), which would hang an automated build. |
| 3–6 | `RUN apt-get update && apt-get install -y --no-install-recommends …` | One layer installing: **python3, pip, venv** (Python); **git, cmake, ninja-build, build-essential, libssl-dev** (needed to *compile* liboqs from C source); **curl, wget** (downloads), **nano** (editor), **iproute2, iputils-ping, tcpdump** (network tools for ping/ip/packet capture), **ca-certificates** (trust HTTPS). `--no-install-recommends` keeps the image small; `rm -rf /var/lib/apt/lists/*` deletes the package index in the **same layer** so it doesn't bloat the image. `&&` chains commands so the layer fails if any step fails. |
| 7 | `RUN python3 -m venv /opt/venv` | Creates a Python **virtual environment**. Needed because Ubuntu 24.04 marks system Python as "externally managed" (PEP 668), so `pip install` system-wide is refused. |
| 8 | `ENV PATH="/opt/venv/bin:$PATH"` | Puts the venv first on PATH, so `python3` and `pip` mean the venv's versions in every later step and in the running container. |
| 9 | `RUN pip install --no-cache-dir cryptography matplotlib pandas liboqs-python` | Installs the libraries: **cryptography** (RSA/ECDSA via OpenSSL), **matplotlib/pandas** (graphs, CSV), **liboqs-python** (Python wrapper for liboqs, the Open Quantum Safe C library). `--no-cache-dir` keeps the image smaller. |
| 10–11 | `RUN python3 -c "import oqs; print(oqs.oqs_version())"` | The first `import oqs` downloads and compiles liboqs. Doing it at **build** time bakes the compiled library into the image, so containers start instantly; it also proves the install works (build fails otherwise). |
| 12 | `WORKDIR /lab` | Default working directory inside the container, where the bind mount appears. |
| 13 | `CMD ["sleep", "infinity"]` | The container's main process. A container stops when its main process exits; `sleep infinity` keeps it alive so we can `docker exec` into it. Exec (JSON) form runs it directly without a shell. |

## 3.2 common.py — shared by every program

| Lines | Explanation |
|---|---|
| 1–8 | Docstring describing the module (Step D2 of the lab). |
| 9–13 | Imports: `hashlib` (SHA-256), `os` (environment, paths), `random` (seeded benchmark message), `sys` (exit with error), `time` (perf_counter_ns). |
| 16–23 | `get_uid()`: reads **STUDENT_UID** from the environment (`os.environ.get`, default empty), strips spaces. Exits with an error if missing, or if not **exactly 10 digits** (`isdigit()` and `len == 10`). `{uid!r}` prints it with quotes so stray spaces are visible. |
| 26 | `UID = get_uid()` runs **at import time**, so every program fails immediately and clearly if the UID is wrong. |
| 30–36 | `ALGS` dictionary: maps the lab names `ecdsa, rsapss, mldsa, slhdsa` to parameters. Classical entries hold curve/hash, key size 3072, e = 65537, salt 32. PQ entries hold the exact **liboqs names** from Step D1. `"family"` lets other code branch classical vs PQ. |
| 37 | `ALG_ORDER`: fixed order for loops, tables and graphs. |
| 40–43 | `check_alg()`: rejects an unknown algorithm name with a helpful message. |
| 48–49 | `P256_N`: the **order n** of the P-256 group (from the lab sheet), as an integer from hex. |
| 52–56 | `document_text()`: amount **A = 1000 + (UID mod 9000)** → 3032; `uid[-4:]` = last 4 digits "0032". Returns the two lines, each ending in `\n` → 59 bytes. |
| 59–62 | `ecdsa_private_scalar()`: SHA-256 of the string `UID + "CNS-DSIG-ECDSA-KEY"` (the `||` is string concatenation), `.encode()` turns text into bytes. `int.from_bytes(…, "big")` turns the 32-byte digest into an integer. `% (n−1)` gives 0…n−2, then **`+ 1` gives 1…n−1**, exactly the valid private-key range (0 is not allowed). |
| 65–67 | `bench_message()`: `random.Random(int(uid))` is a **seeded** Mersenne Twister generator, so the same UID always gives the same 1024 bytes (reproducible). It is **not** cryptographically secure, which is fine for test data, never for keys. |
| 70–72 | `tamper_index()`: **UID mod length**, so the position always lies inside the file. |
| 76 | Folder names: `keys` (private, never shared), `outbox` (public, served by HTTP), `inbox` (received). |
| 79–92 | Path helpers: e.g. `keys/ecdsa_private.key`, `outbox/ecdsa_public.key`, `outbox/ecdsa.sig`, `outbox/document.txt`. `folder=` lets the receiver use `inbox`. |
| 95–97 | `read_bytes()`: opens in **binary** mode `"rb"`, so bytes are signed exactly as stored (no newline or encoding conversion). |
| 100–103 | `write_bytes()`: creates the folder if needed (`exist_ok=True`), writes in binary mode `"wb"`. `or "."` handles a path with no folder. |
| 107–112 | `timed_ms()`: calls any function once between two `perf_counter_ns()` readings and returns (result, milliseconds). `/1e6` converts ns to ms. `*args, **kwargs` forwards any arguments. |

## 3.3 keygen.py — Step D3

| Lines | Explanation |
|---|---|
| 1–9 | Usage and the meaning of `--independent` (used only in Test 4; see Part 4). |
| 12 | `import oqs` — liboqs-python, for ML-DSA and SLH-DSA. |
| 13–14 | From `cryptography`: `serialization` (DER encoding), `ec` and `rsa` key types. |
| 16–17 | Helpers from `common.py`. |
| 20–27 | `_der_pair()`: converts a key object to bytes. Private key: **DER**, format **PKCS8**, **NoEncryption** (no password, as the lab requires; a real system would encrypt it or keep it in an HSM). Public key: **DER**, **SubjectPublicKeyInfo**. Returns (sk, pk). |
| 30–33 | `generate()`. With `--independent` and ECDSA: `ec.generate_private_key(SECP256R1())` picks d from the **OS secure random generator**. |
| 34–36 | Normal ECDSA: `ec.derive_private_key(d, SECP256R1())` builds the key from the **UID-derived d**; the library computes Q = d·G. Deterministic: same UID → same key pair every time. |
| 37–39 | RSA: `rsa.generate_private_key(public_exponent=65537, key_size=3072)` — random primes p, q from the secure generator. |
| 41–44 | ML-DSA / SLH-DSA: `oqs.Signature(name)` creates a signer object for that algorithm. `generate_keypair()` returns the **public key** and keeps the secret inside the object; `export_secret_key()` gets it out as raw bytes. The `with` block frees the C memory afterwards. |
| 47–51 | `main()`: checks 1 or 2 arguments (and that the second is exactly `--independent`); validates the algorithm. |
| 52 | Times key generation with `timed_ms`. |
| 53–54 | Writes the private key into `keys/`, public key into `outbox/`. |
| 55–60 | Prints algorithm, file names and sizes in bytes, and the time. `:28s` and `:6d` are column widths for neat alignment. |
| 63–64 | `if __name__ == "__main__":` — run `main()` only when executed as a script, not when **imported** (bench.py imports `generate` from this file). |

## 3.4 sign.py — Part E

| Lines | Explanation |
|---|---|
| 9–12 | Imports: `oqs`; `hashes` (SHA-256), `ec`, `padding` (PSS, MGF1); `load_der_private_key` (DER bytes → key object). |
| 18–22 | `load_private()`: classical → `load_der_private_key(bytes, password=None)` (no password because we used NoEncryption). PQ → `oqs.Signature(name, sk_bytes)`: a signer object loaded with the raw secret key. |
| 25–28 | ECDSA: `key.sign(data, ec.ECDSA(hashes.SHA256()))` — the library hashes `data` with SHA-256, picks a random nonce k, computes (r, s), and returns DER bytes. |
| 29–34 | RSA-PSS: `key.sign(data, padding.PSS(mgf=MGF1(SHA256), salt_length=32), SHA256())` — PSS padding with MGF1-SHA-256 and a 32-byte random salt, message hashed with SHA-256. |
| 35–36 | ML-DSA / SLH-DSA: `key.sign(data)` — the **whole document** goes in; the algorithm hashes internally (no manual hashing, as the lab requires). |
| 39–42 | `main()`: one argument, validated. |
| 44–47 | Creates `outbox/document.txt` from the UID **only if it does not exist**, so all four algorithms sign the *same* file. |
| 48 | Reads the document as **bytes** (what is signed). |
| 50 | Loads the private key from `keys/`. |
| 51 | Signs (timed). |
| 52 | Writes `outbox/<alg>.sig`. |
| 54–57 | Prints algorithm, document size (59 B), signature size and time. |

## 3.5 verify.py — Part G (and Part H)

| Lines | Explanation |
|---|---|
| 9 | `InvalidSignature`: the exception `cryptography` **raises** when verification fails. |
| 12 | `load_der_public_key`: DER bytes → public key object. |
| 18–22 | `load_public()`: classical → key object; PQ → a tuple (verifier object, raw public key bytes), because liboqs takes the public key as an argument to `verify`. |
| 25–38 | `verify_data()`, classical branch: calls `key.verify(sig, data, …)` with **exactly the same parameters as signing** (ECDSA-SHA256, or PSS/MGF1-SHA256/salt 32/SHA256). If it returns normally → `True`. If it raises `InvalidSignature` → `False`. |
| 39–40 | PQ branch: `verifier.verify(data, sig, pk)` **returns a boolean** directly (liboqs style). |
| 43–45 | `main()`: 1 to 4 arguments (`alg` + optional document, public key, signature). |
| 47–49 | Defaults: `inbox/document.txt`, `inbox/<alg>_public.key`, `inbox/<alg>.sig`. Overriding them is how the tamper tests point to `.tampered` files or a different key. |
| 51 | Reads document and signature bytes. |
| 52–57 | Loads the key and verifies (timed). A **`ValueError`** (e.g. a key file of the wrong type or length) is caught and treated as FAIL, so the program never crashes during the tests. |
| 59–64 | Prints the inputs, time, and `PASS (VALID)` or `FAIL (INVALID)`. |
| 65 | **Exit code 0 for PASS, 1 for FAIL** — useful in scripts (`&&`/`||`). |

## 3.6 tamper.py — Part H (Mallory)

| Lines | Explanation |
|---|---|
| 13–15 | Needs `doc` or `sig` and a file path. |
| 16 | Reads the file into a **bytearray** (mutable, so a byte can be changed). |
| 17 | `idx = UID mod length` → 2 for the 59-byte document, 4 for the 71-byte ECDSA signature, and so on. |
| 18–19 | Saves the old byte, then `data[idx] ^= 0x01`: **XOR with 1 flips the lowest bit** — exactly one bit changes (e.g. 0x61 'a' → 0x60 '\`'). |
| 20–21 | Writes `<file>.tampered`; the **original is never overwritten**, so Test 1 can still use it. |
| 23–25 | Prints file size, index and the byte change in hex (`:02x`). |
| 26–31 | For documents, also prints the character change and the original and modified text (`errors="replace"` avoids crashes on odd bytes). |

## 3.7 bench.py — Part I

| Lines | Explanation |
|---|---|
| 8–13 | `csv` (write results), `platform`/`socket` (Python version, hostname for the log), `statistics` (mean, stdev), `sys`, `time`. |
| 15–18 | **Reuses the real functions** from keygen.py, sign.py and verify.py, so the benchmark measures exactly the same code used in the experiment. |
| 20–21 | 5 warm-up runs; 20 key generations, 100 signings, 100 verifications. |
| 24–33 | `measure(func, runs)`: calls `func` 5 times untimed (warm-up), then `runs` times, **each call timed individually** with `perf_counter_ns()` and converted to ms. Returns the list of times and the last result. |
| 36–38 | `stats()`: mean, **sample standard deviation** (`statistics.stdev`, divides by n−1), min, max. |
| 42 | Output file name (default `results.csv`; we passed `results_run1.csv` etc.). |
| 43–46 | The **1024-byte UID-seeded message**; `assert` checks its length; prints UID, host and a SHA-256 prefix (`c0aa6017dac0b92a`) proving the same message was used every run. |
| 49–51 | For each algorithm: time `generate(alg)` 20 times. `lambda: generate(alg)` wraps the call in a no-argument function so `measure` can call it repeatedly. The **last** key pair is kept. |
| 52 | Converts that key pair into key objects **before** timing, so key loading/parsing is not timed. |
| 54–55 | Times signing the message 100 times, then verifying the last signature 100 times. |
| 57–59 | **Correctness check**: the last signature must verify, otherwise the program stops — we never report timings of failed operations. |
| 61–68 | For each operation, builds a CSV row: uid, algorithm, operation, runs, mean/std/min/max (4 decimals), plus public key, private key and signature sizes; prints a summary line. |
| 69–70 | Prints sizes and `verify-check=PASS`. |
| 72–78 | Writes the CSV with a header row; **uid is the first column** (lab requirement). |

## 3.8 plot.py — Section 15

| Lines | Explanation |
|---|---|
| 11–12 | `matplotlib.use("Agg")`: a backend that draws to files without a screen (containers have no display). Must be set before importing pyplot. |
| 19–22 | Input CSV, document path, output folder `graphs/`, fixed colours per algorithm. |
| 25–34 | Builds the caption from `environment.txt` (CPU, RAM, OS, versions) plus the UID — the lab requires the environment in every caption. |
| 36 | Reads the CSV with pandas; `dtype={"uid": str}` keeps the UID as text. |
| 39 | `x = [0,1,2,3]`: bar positions. |
| 42–43 | `row(alg, op)`: selects the matching CSV row. |
| 46–51 | Key and signature sizes (taken from the "sign" rows; the same in all rows of an algorithm) and the document size. |
| 54–71 | `finish()`: common styling — title, axis labels, ticks, optional **log scale**, grid, legend, caption, tight layout, save as PNG at 150 dpi, close the figure (frees memory). |
| 74–79 | `annotate()`: writes the value above each bar; `tops` lets Graphs 3–4 place labels above the error bar. |
| 82–90 | `bar_with_err()`: bars of mean time with **error bars = standard deviation** (`yerr=std`), log scale. |
| 96–103 | **Graph 1**: grouped bars (public vs private key), each shifted by ±w/2. Log scale because sizes go from 32 B to 2560 B. |
| 105–109 | **Graph 2**: signature sizes, log scale (71 B to 7856 B). |
| 111–115 | **Graphs 3, 4**: signing and verification time with error bars. |
| 117–122 | **Graph 5**: key-generation time. |
| 124–135 | **Graph 6**: **stacked** bars: document at the bottom, signature on top (`bottom=d`), then public key (`bottom=d+s`); total labelled. **Linear** scale so stacked heights add up visually. |
| 137–150 | **Graph 7**: each operation's time divided by ECDSA's time; a dashed line at 1; log scale. |

## 3.9 run_experiment.sh (how your run was automated)

If asked how you ran it: **"I automated the lab-sheet commands in a script. It creates the network and containers, runs each step inside the containers with `docker exec`, and saves every command with its output in `logs/`. The screenshots were made from those logs."** Key parts:
- `h` runs a host command and logs it with your prompt; `c sender …` runs a command inside a container with `docker exec`.
- It starts the HTTP server in the background (`docker exec -d`), downloads with curl from the receiver, runs verify, tamper, bench (3 runs + receiver), picks the median run, runs plot.py and `docker cp`.

---

# Part 4 — Your results explained

### Table 2 — sizes (bytes)
| | Public | Private | Signature | Transmitted |
|---|---|---|---|---|
| ECDSA | 91 | 138 | 71 | 221 |
| RSA-PSS | 422 | 1792 | 384 | 865 |
| ML-DSA-44 | 1312 | 2560 | 2420 | 3791 |
| SLH-DSA-128s | 32 | 64 | 7856 | 7947 |

### Table 4 — timings (ms, median run 3, sender)
| | KeyGen | Sign | Verify | Sign/Verify |
|---|---|---|---|---|
| ECDSA | 0.0922 ± 0.0324 | 0.0442 ± 0.0087 | 0.1239 ± 0.0092 | 0.36 |
| RSA-PSS | 198.13 ± 102.13 | 1.3343 ± 0.0675 | 0.0342 ± 0.0017 | 39.01 |
| ML-DSA | 0.0250 ± 0.0006 | 0.0659 ± 0.0337 | 0.0238 ± 0.0021 | 2.77 |
| SLH-DSA | 55.58 ± 14.48 | 471.38 ± 83.64 | 0.4062 ± 0.0153 | 1160.47 |

### Every "odd-looking" result and its explanation

| Observation | Why |
|---|---|
| ECDSA verify (0.124) is **slower** than sign (0.044); ratio < 1 | Verify = two scalar multiplications (u₁G + u₂Q); sign = one, with precomputed tables for G. |
| RSA verify is **39× faster** than sign | e = 65537 is tiny (17 operations); d is ~3072 bits. |
| RSA keygen has a **huge std** (198 ± 102 ms, min 39, max 383) | Searching for random primes takes a random number of tries. |
| ML-DSA sign std is about half the mean (0.066 ± 0.034) | **Rejection sampling**: a random number of signing attempts. |
| SLH-DSA sign is ~**7,150× ML-DSA** and ~10,700× ECDSA | Rebuilds FORS + 7 layers of hash trees per signature: hundreds of thousands of SHA-256 calls. |
| SLH-DSA verify is fast (0.41 ms) | Only one authentication path per layer is checked. |
| ML-DSA keygen (0.025 ms) is the fastest keygen of all | Sample small vectors, one matrix–vector product with NTT. |
| Single-run times in keygen.py/sign.py are much bigger (e.g. ECDSA sign 13.7 ms vs 0.044 ms) | Those are **first, cold calls** (lazy library initialisation, random-generator setup, cold caches, CPU at low frequency). That is exactly why the benchmark uses warm-ups and repetitions. |
| Benchmark CSV shows ECDSA signature **72 B**, Table 2 shows **71 B** | Different signature (different message and random nonce); DER length is 70–72 depending on leading bits of r and s. |
| Benchmark CSV shows RSA private key **1795 B**, Table 2 shows **1792 B** | Different random RSA key (the benchmark generates new keys); DER integers of p, q, d … vary by leading zero bytes. |
| ECDSA public key is the same every run, but `ecdsa.sig` changes | d comes from the UID (fixed), but every signature uses a **new random nonce k**. |
| Test 4 used `--independent` for ECDSA | The ECDSA key comes from the UID and both containers have the same UID, so the receiver's "own" key would be **identical** to the sender's: not a wrong key. A random key is a genuine wrong key → FAIL. (This also demonstrates the lab's warning: a 10-digit UID is only ~2³³ possibilities, so such keys are brute-forceable.) |
| Sender vs receiver: most operations within ~15%, but ECDSA 2–3× faster on the receiver | Same kernel, same CPU, no network involved, so not Docker. Run-to-run variation: CPU frequency/turbo, the scheduler choosing a **performance or efficiency core** (the i5-1235U has both), background load. |
| Median run chosen by "sum of mean times" | Simple single number per run. Note honestly: it is dominated by SLH-DSA signing and RSA keygen, so it mostly reflects those. An alternative is a per-measurement median. |

### Table 5 — relative to ECDSA (your values)
| | RSA-PSS | ML-DSA | SLH-DSA |
|---|---|---|---|
| Public key | 4.64 | 14.42 | 0.35 |
| Signature | 5.41 | 34.08 | 110.65 |
| Signing | 30.19 | 1.49 | 10664.81 |
| Verification | 0.28 | 0.19 | 3.28 |
| Key generation | 2148.87 | 0.27 | 602.86 |
| Transmitted | 3.91 | 17.15 | 35.96 |

### Table 7 — choices
- Firmware lasting 15 years → **SLH-DSA** (conservative, quantum-safe, rare signing, cheap verify).
- Low-bandwidth sensor → **ECDSA** (smallest signature and key).
- TLS certificate in 2026 → **ECDSA** (universal support, short-lived certificates), moving to hybrid ECDSA + ML-DSA.
- CA root for 30 years → **SLH-DSA**.
- Millions of verifications/second → **ML-DSA** (fastest verify, quantum-safe).

---

# Part 5 — Twisted viva questions (with answers)

### Concepts
1. **Does a digital signature encrypt the message?** No. It provides integrity, authentication and non-repudiation, not confidentiality. Our document crossed the network in plain text.
2. **"Signing = encrypting with the private key." True?** Only loosely for textbook RSA. It is wrong in general: ECDSA, ML-DSA and SLH-DSA are not encryption at all, and even RSA signing uses padding (PSS) different from RSA encryption padding.
3. **If the SHA-256 matched on both sides, why do we need signatures?** A hash has no key. Mallory can change the file and recompute its hash. A signature needs SK, which she doesn't have.
4. **Can Mallory replay the signed document?** Yes! The signature on "Transfer Rs.3032" is valid forever, so she could resend it to get the transfer done twice. Signatures don't stop replay; the signed content must include a **nonce, timestamp or sequence number**.
5. **What if two documents have the same hash?** (A collision.) Then a signature on one is valid for the other. SHA-256 has no known collisions; that's why MD5/SHA-1 are banned for signatures.
6. **Why hash before signing?** Fixed size input that fits the algorithm, speed, and the hash's security properties. ML-DSA/SLH-DSA hash internally.
7. **What is EUF-CMA?** Existential unforgeability under chosen-message attack: even after seeing signatures on messages of his choice, the attacker cannot produce a valid signature on any new message.
8. **Difference between second pre-image and collision resistance?** Second pre-image: given a specific M, find M′ with the same hash. Collision: find any pair. Collisions are easier (birthday bound 2^(n/2)).

### RSA
9. **Why e = 65537?** Small (fast verification), only two 1-bits (17 multiplications), and large enough to avoid small-exponent attacks that affect e = 3.
10. **Why PSS and not textbook RSA?** Textbook RSA is malleable and allows existential forgery. PSS adds a random salt and structured padding, with a security proof.
11. **Why does signing the same document twice with RSA-PSS give different signatures? Does verification still work?** The random salt. Yes: the verifier recovers the salt from the signature.
12. **Why salt length 32?** Equal to the SHA-256 output length (RFC 8017 recommendation). Verification must use the same setting.
13. **What does MGF1 do?** Stretches a hash into a mask of any length: H(seed‖counter) for counter = 0, 1, 2, … concatenated.
14. **Why is RSA-3072 used, not 2048?** 3072-bit ≈ 128-bit security, matching P-256 and the PQ schemes. RSA-2048 is ≈ 112-bit.
15. **Your RSA signature is 384 bytes. Why exactly?** It is a number mod n, and n is 3072 bits = 384 bytes.

### ECDSA
16. **Write the ECDSA signing equation.** r = (k·G).x mod n, s = k⁻¹(h + r·d) mod n.
17. **What happens if k is reused?** From two signatures with the same r: k = (h₁ − h₂)/(s₁ − s₂), then d = (s·k − h)/r. Private key leaked (PS3 hack).
18. **Your ECDSA key comes from the UID. Is your signature deterministic?** No. d is fixed, but k is random each time; my `ecdsa.sig` changed between runs while the public key did not.
19. **Why `mod (n−1) + 1` in the key derivation?** Valid d must be in 1…n−1; mod (n−1) gives 0…n−2, +1 shifts it into range (d = 0 is invalid).
20. **Is a UID-derived key secure?** No: only 10¹⁰ ≈ 2³³ possible UIDs; an attacker can try them all in seconds. It's only for individualising the lab.
21. **Why is your ECDSA signature 71 bytes and not 64?** DER encoding: SEQUENCE and INTEGER headers, plus a leading 00 when the top bit of s is 1 (my s starts 0xBE). Lengths vary 70–72.
22. **Which byte did tamper.py flip in your ECDSA signature and what did that do?** Byte 4 = first byte of r (0x65 → 0x64). The verifier's computed X.x no longer equals r → FAIL.
23. **Could flipping a different bit make parsing fail rather than verification?** Yes: flipping a DER header byte (e.g. byte 0) makes the signature unparsable; the library still reports InvalidSignature → FAIL.
24. **What is ECDSA malleability?** (r, n−s) is also valid for the same message.
25. **Why is ECDSA verify slower than sign?** Two scalar multiplications vs one fixed-base multiplication.

### Post-quantum
26. **Does Shor break AES or SHA-256?** No. Grover only halves their security bits (256 → 128), so they remain safe.
27. **Why doesn't increasing RSA key size help against Shor?** Shor runs in polynomial time; key size only grows the work polynomially.
28. **Is ML-DSA the same as ML-KEM?** No. ML-KEM (FIPS 203) is key encapsulation for key exchange; ML-DSA (FIPS 204) is signatures.
29. **What is rejection sampling in ML-DSA and how did you see it?** The signer restarts if z would leak secret information. Visible as high signing std (0.066 ± 0.034 ms) vs steady verify.
30. **Why is SLH-DSA called stateless? What is the alternative?** It chooses one-time keys pseudo-randomly from the message, so no counter is stored. XMSS/LMS are stateful and catastrophic if state is reused.
31. **Derive the SLH-DSA-128s signature size.** 16 + 14·13·16 + (63 + 7·35)·16 = 16 + 2912 + 4928 = 7856 bytes.
32. **How can SLH-DSA's public key be only 32 bytes?** It's a 16-byte seed plus the 16-byte root of the top Merkle tree. All the security is in the hash function.
33. **What does "s" in 128s mean? What would "f" change?** Small signature, slow signing. 128f: faster signing, ~17 KB signatures.
34. **Is comparing ML-DSA-44 (category 2) with SLH-DSA-128s (category 1) fair?** Both are in the ~128-bit class, like RSA-3072 and P-256, as the lab sheet intended.
35. **Why are PQ signatures needed if no quantum computer exists yet?** Long-lived signatures must still be trustworthy after one exists; migration (standards, hardware, certificates) takes years.
36. **Why hybrids?** Secure while either algorithm stands; the PQ schemes are young.

### Encodings
37. **Someone measured ECDSA keys as 178/241 bytes. Who is right?** Both. They used **PEM** (Base64 + headers); I used **DER** as Step D3 requires. Same key, different encoding.
38. **What is inside SubjectPublicKeyInfo?** An algorithm identifier (OID for EC public key + OID for P-256) and the key bits (04 ‖ x ‖ y).
39. **Why are ML-DSA/SLH-DSA sizes exactly the standard values but ECDSA/RSA not?** liboqs stores raw keys; classical keys are wrapped in DER structures.

### Docker and networking
40. **Is a container a VM?** No. It shares the host kernel; isolation is from namespaces and cgroups.
41. **How did `curl http://sender:8000` find the sender?** Docker's embedded DNS (127.0.0.11) on the user-defined network resolves container names to IPs.
42. **Would it work on the default bridge network?** Not by name; the default bridge has no automatic name resolution (only IPs or legacy `--link`).
43. **You never used `-p 8000:8000`. How did the receiver reach port 8000?** Containers on the same network can reach all each other's ports. `-p` only publishes a port to the host.
44. **What is 172.18.0.1?** The gateway: the host's side of the sig-net bridge.
45. **Why `sleep infinity`?** A container stops when its main process ends; this keeps it running for `docker exec`.
46. **`--name` vs `--hostname`?** `--name`: Docker's name and DNS name on the network. `--hostname`: the name inside the container (in the prompt).
47. **Where were the files if the container is deleted?** On the host, in `~/sig-lab/sender` and `~/sig-lab/receiver`, because of the bind mounts.
48. **Why a virtual environment inside Docker?** Ubuntu 24.04 blocks system-wide `pip install` (PEP 668, externally managed environment).
49. **Why combine `apt-get update && install && rm -rf lists` in one RUN?** One layer; deleting the index in a later layer would not reduce image size.
50. **Why does the Dockerfile run `import oqs` during the build?** It compiles liboqs into the image, so containers don't recompile it at start-up, and proves the install works.
51. **ttl = 64 in ping — what does it tell you?** Linux's default TTL, not decremented: no router between the containers (same bridge).
52. **Why was the first ping slower?** ARP resolution (finding the MAC address) and cold caches.
53. **Does the private key ever cross the network?** No. Only `outbox/` was served; the HTTP log shows 9 GETs, none for keys.
54. **The HTTP log shows 172.18.0.3. What is it?** The receiver's IP: the client making the requests.

### Benchmarking
55. **Why perf_counter_ns and not time.time?** Monotonic (not affected by clock changes), highest resolution, integer nanoseconds.
56. **Why warm-up runs?** First calls include one-time initialisation, cold caches and CPU frequency ramp-up.
57. **Why time each call individually instead of the whole loop?** To get standard deviation, min and max, not just an average.
58. **Was file I/O inside your timing?** No. The message was in memory; keys were loaded before timing; only the crypto call was between the two clock readings.
59. **Does Docker affect your timings?** Not meaningfully: containers run directly on the kernel. The network was not involved in the benchmark at all.
60. **Why is min useful?** It is the least disturbed run, closest to the true cost of the operation.
61. **Why 20 runs for keygen but 100 for sign/verify?** Key generation is slow for RSA (and SLH-DSA); signing/verifying is fast enough to repeat 100 times (except SLH-DSA signing, which still takes ~47 s total).
62. **Why does `statistics.stdev` use n−1?** Sample standard deviation (Bessel's correction) for an unbiased estimate from a sample.
63. **Your sender and receiver gave different ECDSA times. Why, if it's the same machine?** Run-to-run variation: CPU frequency/turbo, performance vs efficiency cores on the i5-1235U, background load. Not the network.

### Code
64. **Why read files in binary mode?** To sign exactly the stored bytes; text mode could change line endings or encoding.
65. **Why does tamper.py write a new file instead of editing the original?** To keep the original for Test 1 and for comparison.
66. **What does `^= 0x01` do?** XOR with 1 flips the lowest bit, so exactly one bit (one character) changes.
67. **How does verify.py handle the two libraries' different failure styles?** `cryptography` raises `InvalidSignature` (caught → False); liboqs returns a boolean.
68. **Why does bench.py verify the signature after the loops?** So it never reports timings of failing operations.
69. **Why `if __name__ == "__main__"`?** So bench.py can import `generate`, `sign_data` and `verify_data` without running the scripts' `main()`.
70. **Why `matplotlib.use("Agg")`?** No display inside a container; Agg draws straight to PNG files.
71. **Why a log scale in Graphs 1–5 and 7 but not 6?** Values span orders of magnitude (e.g. 0.024 ms to 471 ms). Graph 6 is stacked, and stacked heights only add up visually on a linear scale.
72. **Your keys are stored unencrypted. Is that OK?** For the lab, yes (the sheet says NoEncryption PKCS#8). In real systems: encrypted PKCS#8 with a password, or an HSM / smart card, and file permissions like 600.

---

# Part 6 — Cheat sheet

| Item | Value |
|---|---|
| UID | 2024300032 |
| Document | "Transfer Rs.3032 to Account 0032" / "Issued by UID: 2024300032" — 59 bytes |
| A | 1000 + (UID mod 9000) = 3032 |
| ECDSA d | SHA-256(UID‖"CNS-DSIG-ECDSA-KEY") mod (n−1) + 1 = 0x32254748… |
| Tamper indices | doc 2 ('a'→'\`'); ECDSA 4; RSA 256; ML-DSA 1492; SLH-DSA 5232 |
| Network | sig-net, bridge, 172.18.0.0/16, gateway .1, sender .2, receiver .3 |
| Sizes (pk/sk/sig) | ECDSA 91/138/71 · RSA 422/1792/384 · ML-DSA 1312/2560/2420 · SLH-DSA 32/64/7856 |
| Transmitted | 221 · 865 · 3791 · 7947 bytes |
| Fastest sign / verify | ECDSA 0.044 ms / ML-DSA 0.024 ms |
| Slowest | SLH-DSA sign 471 ms; RSA keygen 198 ms |
| Benchmark | 5 warm-ups; 20/100/100 runs; 3 runs; median = run 3 |
| Standards | RSA-PSS: RFC 8017/FIPS 186-5 · ECDSA: FIPS 186-5 · ML-DSA: FIPS 204 · SLH-DSA: FIPS 205 (Aug 2024) |
| Hard problems | factoring · ECDLP · Module-LWE/SIS · hash functions only |
| Shor-resistant | No · No · Yes · Yes |
| Environment | i5-1235U, 12 threads, 3.7 GiB (WSL2), Ubuntu 24.04.5, Docker 29.8.2, cryptography 50.0.2, liboqs 0.16.0 |
