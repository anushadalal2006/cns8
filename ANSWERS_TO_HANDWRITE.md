# Exp 8: Answers to write by hand

**Name:** Anusha Dalal **UID:** 2024300032

All numbers below come from your measured data (Tables 2 to 5). Copy them as they are so they match the tables document.

---

## 17. Discussion Questions

### Conceptual

**1. What are the three algorithms of a digital-signature scheme? Which key is used in which algorithm?**

- **KeyGen() → (PK, SK)** generates the key pair. It takes no key as input, only randomness.
- **Sign(SK, M) → S** uses the **private key SK**, which only the signer knows.
- **Verify(PK, M, S) → accept / reject** uses the **public key PK**, which anyone can have.

In hash-and-sign schemes (RSA-PSS, ECDSA), the signer signs the digest h = H(M). ML-DSA and SLH-DSA take the whole message and hash it internally.

**2. What is the difference between a digital signature and a MAC (e.g. HMAC)? Why does the signature allow non-repudiation?**

A MAC uses one **shared secret key** both to create and to check the tag. Both parties can therefore produce the same tag, so a third party cannot tell which of them made it. It gives integrity and authentication only between the two key holders.

A signature uses a **key pair**. Only the holder of SK can create S, while anyone with PK can verify it. The verifier cannot create signatures, so a valid signature proves to anyone (for example a judge) that the owner of SK signed the message. The signer cannot later deny it: this is **non-repudiation**.

**3. Why is the private key never transferred in this experiment? What would happen if it were?**

Verification needs only PK, and the whole scheme is secure only while SK stays with the signer. Our channel was plain HTTP on sig-net, which anyone on the network can read. If SK were sent, an eavesdropper (Mallory) could sign any document, e.g. "Transfer Rs.99999", and it would verify as PASS. Integrity, authentication and non-repudiation would all be lost, and the key would have to be revoked. That is why outbox/ held only public files and keys/ was never served.

**4. Why did post-quantum cryptography come into the picture? Explain Shor's algorithm's effect on RSA and ECDSA, and why a signature that is valid today may be dangerous to rely on in 20 years.**

RSA is safe because factoring n = p·q is hard. ECDSA is safe because finding d from Q = d·G (the elliptic-curve discrete logarithm) is hard. **Shor's algorithm**, on a large fault-tolerant quantum computer, solves both in polynomial time. An attacker could then compute the private key directly from the public key and forge any signature, and bigger key sizes do not help.

Grover's algorithm only weakens hash functions quadratically, and no efficient quantum attack is known on lattices. So in August 2024 NIST standardised **ML-DSA** (lattice-based) and **SLH-DSA** (hash-based).

Long-lived signatures are the danger: firmware, root certificates, legal archives. Once a quantum computer exists, an attacker can recover today's RSA/ECDSA key and create "new" signatures that look exactly like genuine ones. A verifier in 20 years then cannot tell a real 2026 document from a forged one.

### Analytical (measured data)

**5. Which algorithm had the smallest and which the largest signature? Express the difference as a ratio and explain the cause.**

- Smallest: **ECDSA, 71 B**.
- Largest: **SLH-DSA, 7856 B**, which is **110.6 ×** ECDSA (3.25 × ML-DSA's 2420 B and 20.5 × RSA's 384 B).

ECDSA's signature is just two 32-byte numbers (r, s) in DER format, because elliptic curves give 128-bit security with 256-bit numbers. An SLH-DSA signature must carry a FORS signature plus a WOTS+ one-time signature and a Merkle authentication path for every layer of the hypertree. That is hundreds of 16-byte hash values. ML-DSA's signature is a vector of polynomials (256 coefficients each), so its size falls in between.

**6. Which algorithm was fastest to sign and which to verify? Why is SLH-DSA signing much slower than ML-DSA signing?**

- Fastest signing: **ECDSA, 0.056 ms** (ML-DSA 0.104 ms).
- Fastest verification: **ML-DSA, 0.036 ms** (RSA-PSS 0.059 ms, ECDSA 0.129 ms).
- SLH-DSA signing took **839.8 ms**, about **8000 ×** ML-DSA.

ML-DSA signing is a few polynomial multiplications (NTT) with occasional rejection-sampling retries. SLH-DSA is stateless, so every signature must recompute, from the secret seed, the FORS trees and the WOTS+ chains and Merkle trees of each hypertree layer. That is hundreds of thousands of SHA-256 calls. The "s" (small) variant uses tall trees to shrink the signature, which makes signing even slower. Verification recomputes only one path, so it stays fast (0.665 ms).

**7. SLH-DSA has a tiny public key (32 B) but a large signature; ML-DSA has a larger public key but a smaller signature. Discuss the trade-off for a system that sends one public key but millions of signatures.**

The total cost is PK + N × |S|:
- ML-DSA: 1312 + 2420·N bytes.
- SLH-DSA: 32 + 7856·N bytes.

SLH-DSA's small key only wins if no signature is ever sent. Even at N = 1, ML-DSA is smaller (3732 B vs 7888 B). For one million signatures, ML-DSA needs about **2.42 GB** and SLH-DSA about **7.86 GB** (3.2 × more), so the public-key size becomes irrelevant. SLH-DSA also signs about 8000 × slower. ML-DSA is therefore better for high-volume signing. SLH-DSA's tiny key helps only where the key must be stored in very small memory (boot ROM, a certificate) and few signatures are made.

**8. The public key was fetched over the same untrusted channel as the document. Explain how a man-in-the-middle could defeat the scheme and how certificates and a PKI solve this.**

Mallory, sitting between the containers or pretending to be "sender", can replace all three files. She makes her own key pair, writes her own document, signs it with her SK and delivers her PK. The receiver verifies Mallory's signature with Mallory's key and gets **PASS**. Verification proves only that the document matches *that* key, not who owns the key.

**PKI solves this.** A trusted Certificate Authority signs a **certificate** that binds PK_A to Alice's identity. The receiver checks the certificate chain up to a root CA key it already trusts (pre-installed in its trust store), and checks validity dates and revocation. Key fingerprints compared over a separate trusted channel, or key pinning, also work.

### Application and evaluation

**9. Is ML-DSA or SLH-DSA "better" than ECDSA? Answer using your data, and consider size, speed, maturity and quantum security. Is there a single winner?**

**No single winner.**
- **Size:** ECDSA wins. It transmitted 221 B, against 3791 B for ML-DSA (17.2 ×) and 7947 B for SLH-DSA (36 ×).
- **Speed:** ML-DSA is about as fast as ECDSA or faster: key generation 0.59 ×, signing 1.87 ×, verification 0.28 × ECDSA's time. SLH-DSA signs about 15 000 × slower than ECDSA.
- **Maturity:** ECDSA has decades of analysis and support everywhere. ML-DSA and SLH-DSA were only standardised in 2024.
- **Quantum security:** only ML-DSA and SLH-DSA survive Shor's algorithm, and SLH-DSA rests on the safest assumption (hash functions only).

So: ECDSA for size-critical, short-lived uses today; ML-DSA as the general post-quantum replacement; SLH-DSA for long-lived roots of trust.

**10. Why do many experts recommend hybrid signatures (classical + post-quantum) during the transition period?**

A hybrid signature is accepted only if **both** signatures verify. It therefore stays secure as long as **at least one** of the two algorithms is unbroken. The post-quantum schemes are new, and attacks or implementation bugs (side channels) may still be found; some PQ candidates such as Rainbow and SIKE were broken recently. The classical scheme is well studied but will fall to a quantum computer. A hybrid protects against both risks. It also satisfies regulations that still require FIPS 186 algorithms and lets older verifiers keep working. The price is both sizes added together: ECDSA + ML-DSA = 2491 B of signature.

**11. Does the Docker network affect the cryptographic measurements? How did you keep Docker, the network and file I/O out of your timings, and what other factors (CPU frequency, background load, container CPU limit) can still influence them?**

No. The network affects only the file transfer, not the computation. In bench.py:
- The 1024-byte message is created in memory.
- Keys are loaded before the timed region.
- Only the single library call (keygen / sign / verify) sits between two time.perf_counter_ns() calls, with no file or network I/O inside the loop.
- The containers were already running.
- 5 warm-up calls were discarded, and many repetitions gave mean, std, min and max.
- The last signature was checked so that failed operations were not timed.

A container is a normal process on the host kernel, so CPU-bound code runs at native speed. The sender and receiver results agreed within noise.

Factors that can still affect timings: CPU frequency scaling or turbo and temperature, background load on the machine (visible as outliers in max_ms), OS scheduling and caches, a container CPU limit (--cpus), Python call overhead, library build options (AVX2), and the random time RSA takes to find primes (hence its large std).

### Questions referred to in the lab sheet (only if your instructor asks)

- **Think box (Part F):** see Q8. In practice the public key comes inside a CA-signed certificate (PKI), or is checked by fingerprint over a trusted channel.
- **UID-derived key warning (Section 5):** a 10-digit UID gives only about 10¹⁰ ≈ 2³³ possibilities, so an attacker can try every UID in seconds and recover the ECDSA private key. We saw this in Test 4: running the UID-based keygen on the receiver rebuilt the sender's exact ECDSA key, so for a genuinely wrong key we had to generate an independent one from the secure random generator. Real keys must always come from a cryptographically secure random generator.

---

## 18. Final Conclusion (249 words, within the 200–250 limit)

A digital signature gives integrity and authentication because only the holder of the private key can produce a signature, while anyone holding the matching public key can check it; the private key never left the sender's container, and only the document, signature and public key crossed the sig-net network. Changing a single character of the document or a single bit of the signature made verification fail for all four algorithms, as did verifying with an unrelated public key. For that wrong-key test ECDSA needed an independent random key, because a key derived from my UID would have been identical to the sender's, showing why low-entropy keys are dangerous. ECDSA had the smallest footprint (71-byte signature, 221 bytes transmitted), RSA-PSS verified quickly but needed slow key generation, ML-DSA-44 was as fast as or faster than ECDSA but transmitted 3,791 bytes, and SLH-DSA had a 32-byte public key but a 7,856-byte signature and 840 ms signing. Post-quantum signatures are necessary because Shor's algorithm would break RSA and ECDSA, letting attackers forge signatures on documents that must stay trustworthy for decades; the price is larger keys and signatures and, for SLH-DSA, slower signing. For today's bandwidth-sensitive applications I would choose ECDSA; for general post-quantum use ML-DSA; and for long-term roots of trust and firmware SLH-DSA, whose security rests only on hash functions. I learned to build one image, run isolated containers on a user-defined network, reach them by name, use bind mounts to keep results, and keep container overhead out of measurements.
