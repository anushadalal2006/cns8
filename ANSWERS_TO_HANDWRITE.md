# Exp 8: Answers to write by hand

**Name:** Anusha Dalal **UID:** 2024300032

All numbers below come from your measured data (Tables 2 to 5). Copy them as they are so they match the tables document.

---

## 17. Discussion Questions

### Conceptual

**1. What are the three algorithms of a digital-signature scheme? Which key is used in which algorithm?**

- **KeyGen() → (PK, SK):** creates the key pair; uses no key.
- **Sign(SK, M) → S:** uses the **private key SK**.
- **Verify(PK, M, S) → accept / reject:** uses the **public key PK**.

RSA-PSS and ECDSA sign the hash h = H(M); ML-DSA and SLH-DSA hash the message internally.

**2. What is the difference between a digital signature and a MAC (e.g. HMAC)? Why does the signature allow non-repudiation?**

A MAC uses one **shared secret key** to create and check the tag, so either party could have made it. A signature uses a **key pair**: only the SK holder can sign, anyone with PK can verify. Since the verifier cannot sign, a valid signature proves the signer signed it and they cannot deny it (**non-repudiation**).

**3. Why is the private key never transferred in this experiment? What would happen if it were?**

Verification needs only PK, and security depends on SK staying secret. Our HTTP channel was readable by anyone, so a leaked SK would let an attacker sign any document (e.g. "Transfer Rs.99999") that verifies as PASS. Integrity, authentication and non-repudiation would be lost and the key would have to be revoked.

**4. Why did post-quantum cryptography come into the picture? Explain Shor's algorithm's effect on RSA and ECDSA, and why a signature that is valid today may be dangerous to rely on in 20 years.**

RSA relies on factoring and ECDSA on the elliptic-curve discrete log. **Shor's algorithm** on a large quantum computer solves both efficiently, so the private key can be computed from the public key and any signature forged; bigger keys do not help. Lattice and hash problems have no such attack, so NIST standardised **ML-DSA** and **SLH-DSA** (2024). Long-lived signatures (firmware, certificates, legal records) are the danger: once the old key is broken, forgeries look genuine, so in 20 years a real document cannot be told from a fake.

### Analytical (measured data)

**5. Which algorithm had the smallest and which the largest signature? Express the difference as a ratio and explain the cause.**

Smallest: **ECDSA, 71 B**. Largest: **SLH-DSA, 7856 B**, i.e. **110.6 ×** larger. An ECDSA signature is just two 32-byte numbers (r, s). An SLH-DSA signature must contain many hash values: a FORS signature plus a one-time signature and a Merkle authentication path for every hypertree layer.

**6. Which algorithm was fastest to sign and which to verify? Why is SLH-DSA signing much slower than ML-DSA signing?**

Fastest signing: **ECDSA (0.044 ms)**. Fastest verification: **ML-DSA (0.024 ms)**. SLH-DSA signing took **471.4 ms**, about **7150 ×** ML-DSA. ML-DSA signing is a few polynomial multiplications, while SLH-DSA must rebuild large hash trees from its seed for every signature (hundreds of thousands of hash calls). Verification only checks one path, so it stays fast (0.406 ms).

**7. SLH-DSA has a tiny public key (32 B) but a large signature; ML-DSA has a larger public key but a smaller signature. Discuss the trade-off for a system that sends one public key but millions of signatures.**

The cost is PK + N × signature. For one million signatures ML-DSA needs about **2.42 GB** and SLH-DSA about **7.86 GB** (3.2 × more); the key size becomes irrelevant (ML-DSA is already smaller at N = 1). SLH-DSA also signs about 7150 × slower, so **ML-DSA** suits high volume; SLH-DSA's tiny key helps only where few signatures are made and key storage is tight.

**8. The public key was fetched over the same untrusted channel as the document. Explain how a man-in-the-middle could defeat the scheme and how certificates and a PKI solve this.**

Mallory can replace the document, signature **and** public key with her own; the receiver then verifies her signature with her key and gets PASS, because verification does not prove who owns the key. A **certificate** signed by a trusted **CA** binds PK to the sender's identity; the receiver checks the chain up to a pre-trusted root (and expiry and revocation).

### Application and evaluation

**9. Is ML-DSA or SLH-DSA "better" than ECDSA? Answer using your data, and consider size, speed, maturity and quantum security. Is there a single winner?**

**No single winner.**
- **Size:** ECDSA sends 221 B vs 3791 B (ML-DSA) and 7947 B (SLH-DSA).
- **Speed:** ML-DSA is comparable to ECDSA (signing 1.49 ×, verification 0.19 ×); SLH-DSA signs about 10 700 × slower.
- **Maturity:** ECDSA is decades old; ML-DSA and SLH-DSA date from 2024.
- **Quantum security:** only ML-DSA and SLH-DSA are safe.

So: ECDSA for compact, short-lived uses today; ML-DSA as the general post-quantum choice; SLH-DSA for long-lived roots of trust.

**10. Why do many experts recommend hybrid signatures (classical + post-quantum) during the transition period?**

A hybrid is valid only if **both** signatures verify, so it stays secure while **either** algorithm is unbroken. The new PQ schemes may still have undiscovered flaws (e.g. Rainbow and SIKE were broken), while classical schemes will fall to quantum computers. Hybrids also keep compatibility and compliance during migration, at the cost of both sizes (ECDSA + ML-DSA = 2491 B).

**11. Does the Docker network affect the cryptographic measurements? How did you keep Docker, the network and file I/O out of your timings, and what other factors (CPU frequency, background load, container CPU limit) can still influence them?**

**No:** the network only affects the file transfer. bench.py creates the message in memory, loads keys first, and times only the single sign / verify / keygen call with perf_counter_ns, with no file or network I/O inside; it uses 5 warm-up runs and many repetitions. Sender and receiver mostly agreed within 15 %, but ECDSA was 2–3 × faster on the receiver. Remaining influences: CPU frequency and turbo, performance vs efficiency cores (i5-1235U), background load, container CPU limits (--cpus) and RSA's random prime search.

---

## 18. Final Conclusion (243 words, within the 200–250 limit)

A digital signature gives integrity and authentication because it binds the document's hash to the signer: only the holder of the private key can produce it, while anyone holding the matching public key can verify it. The private key never left the sender's container; only the document, signature and public key crossed the sig-net network. Changing one character of the document or one bit of the signature made verification fail for all four algorithms, as did verifying with a different public key. For that test ECDSA needed an independent random key, because a key derived from my UID equalled the sender's, showing why low-entropy keys are dangerous. ECDSA had the smallest footprint (71-byte signature, 221 bytes transmitted), RSA-PSS verified quickly but generated keys slowly, ML-DSA-44 was roughly as fast as ECDSA but transmitted 3,791 bytes, and SLH-DSA had a 32-byte public key but a 7,856-byte signature and 471 ms signing. Post-quantum signatures are needed because Shor's algorithm would break RSA and ECDSA, allowing forgeries on documents that must stay trustworthy for decades; the price is larger keys and signatures and, for SLH-DSA, slow signing. Today I would choose ECDSA, which is compact, fast and universally supported; for long-term security, ML-DSA generally and SLH-DSA for firmware and root keys, since it relies only on hash functions. I learned to build one image, run isolated containers on a user-defined network, reach them by name, keep results with bind mounts, and exclude container overhead from measurements.
