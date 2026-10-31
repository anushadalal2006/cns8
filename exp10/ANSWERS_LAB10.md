# Lab 10 — Secure E-mail using PGP and S/MIME: answers

**Name:** Anusha Dalal **UID:** 2024300032

Values marked **[from your run]** are filled in from your own run once it is pushed.

---

## Table 2: PGP Results

| Test | Expected result | Observed result / evidence |
|---|---|---|
| Public key export/import | Keys imported; fingerprints can be inspected | Both keys exported as ASCII-armored .asc files and imported into the other keyring ("public key imported"); fingerprints shown with `gpg --fingerprint` [from your run] |
| Detached signature on original message | Good signature (trust status noted separately) | **Good signature from "Alice CNS Lab <alice-lab@example.test>" [unknown]**; separately: WARNING, the key is not certified with a trusted signature |
| Encrypt for Bob and decrypt as Bob | Decryption succeeds; content matches original | Decrypted with Bob's rsa3072 subkey; `decrypted_message.txt` = "CNS Lab: PGP secure e-mail test. Message ID: CNS-PGP-01." |
| Signed-and-encrypted message | Bob decrypts and signature status is displayed | Bob decrypted it and GnuPG showed **Good signature** from Alice (with the same trust warning); content matches |
| Modified message checked against original signature | Signature verification fails | **BAD signature from "Alice CNS Lab"** (tampered.txt had "ALTERED" appended) |
| Attempt to decrypt with a non-matching private key (optional) | Decryption fails | Alice tried to decrypt the message for Bob: **"decryption failed: No secret key"** |

## Table 3: S/MIME Results

| Test | Expected result | Observed result / evidence |
|---|---|---|
| Inspect Alice/Bob certificate | Subject, issuer and validity displayed | Subject CN=Alice CNS Lab / CN=Bob CNS Lab with their e-mail addresses; issuer CN=CNS Lab CA; valid 180 days [from your run] |
| Verify original signed message using lab CA | Verification succeeds | **Verification successful**; recovered text written to verified_message.txt |
| Encrypt for Bob and decrypt using bob.key | Decryption succeeds; content matches original | encrypted.eml is enveloped-data (smime.p7m); decryption succeeded; message body identical to message.txt (only the MIME header added by `-text` and CRLF line endings differ) |
| Sign and encrypt workflow | Bob recovers the signed message | Bob decrypted signed_encrypted.eml, **Verification successful** on the recovered signed message, body identical to message.txt |
| Modified signed content | Signature verification fails | **Verification failure**: `PKCS7_signatureVerify: digest failure` and `signature failure` (one character changed: "test" → "tost") |
| Verify with untrusted/missing CA | Certificate trust validation fails or warns | With another CA or no -CAfile: **Verification failure: unable to get local issuer certificate** (a trust failure). With `-noverify` the same message verifies, so the signature itself is valid |

---

## Comparative analysis (3–5 sentences)

PGP was easier to set up in the lab: each user generated a key pair and exchanged public keys directly, with no third party. Its extra trust step is manual: each user must compare the full key fingerprint over a separate trusted channel (and could certify the key), otherwise GnuPG warns that the key is not certified. S/MIME needed more setup, because a CA had to be created first and had to issue a certificate for each user. In return, the recipient only has to trust the CA certificate, after which every certificate it issued can be validated automatically, but the CA's issuance, chain validation, renewal and revocation must be managed.

---

## Discussion questions

**1. PGP vs S/MIME: key management and trust model.**
PGP users create and exchange their own key pairs, and trust is decentralised: you decide who to trust by checking fingerprints or through signatures from people you trust (web of trust). S/MIME uses X.509 certificates issued by a Certificate Authority; trust is hierarchical, so you trust the CA and therefore every certificate in its chain.

**2. Why hybrid encryption?**
Symmetric encryption (e.g. AES) is fast and suits large message content, but needs a shared key. Public-key encryption solves key distribution but is slow and limited in size. So a random one-time session key encrypts the message, and only that small key is encrypted with the recipient's public key.

**3. Signing and verifying keys.**
The sender signs with **her own private key**; anyone verifies with the **sender's public key** (in S/MIME, the public key inside her certificate).

**4. Encrypting for Bob and decrypting.**
The message is encrypted with **Bob's public key** (his certificate in S/MIME); Bob decrypts with **his own private key**.

**5. Why never send private keys?**
Whoever has a private key can decrypt everything sent to that person and sign messages in their name. The transfer folder and e-mail are insecure channels, so a sent private key must be assumed compromised; confidentiality, authentication and non-repudiation would all be lost.

**6. Valid signature vs trusted identity.**
A valid signature only proves the message was signed by the private key matching the public key used, and was not changed. It does not prove whose key it is. Trust in the identity needs separate checking: fingerprint verification (PGP) or a valid CA chain (S/MIME). That is why GnuPG said "Good signature" and also "not certified with a trusted signature".

**7. Why import without fingerprint check enables MITM.**
An attacker on the channel could replace Alice's public key with their own key carrying Alice's name. Bob would then accept the attacker's signatures as Alice's, and messages Bob encrypts "to Alice" could be read by the attacker. Comparing the full fingerprint over a trusted channel detects the substitution.

**8. Role of the CA certificate in S/MIME verification.**
It is the trust anchor. OpenSSL checks that Alice's certificate was signed by a CA in the -CAfile; with the CA it reported "Verification successful", and without it "unable to get local issuer certificate", even though the signature itself was valid.

**9. What happened when the message was modified?**
Verification failed: GnuPG reported "BAD signature" and OpenSSL "digest failure". The signature is over a hash of the exact content; any change gives a different hash that no longer matches the signed hash, so integrity violation is detected.

**10. Why is a lab/self-signed certificate not trusted in production?**
Mail clients trust only CAs in their built-in trust store, which are audited and verify identities. Our lab CA is not in that store, and anyone can create a self-signed CA claiming any name, so trusting it automatically would let attackers forge identities.

**11. Can a signed message also be encrypted?**
Yes. Sign first, then encrypt: the signature covers the real content and is itself hidden inside the encryption, so only Bob sees who signed and what was signed. Bob decrypts first, then verifies. We did this in both parts (`--sign --encrypt` in PGP; sign then encrypt in S/MIME).

**12. One advantage and one limitation of each.**
- **PGP:** advantage: free, no CA needed, users control their own keys. Limitation: key authenticity depends on users checking fingerprints; weak usability for non-experts.
- **S/MIME:** advantage: built into enterprise mail clients, and automatic validation through a CA chain. Limitation: requires obtaining, renewing and revoking certificates from a CA (cost and management overhead).

---

## Conclusion (150–200 words)

> In this experiment I implemented secure e-mail with PGP using GnuPG and with S/MIME using OpenSSL. In PGP, Alice and Bob generated RSA 3072-bit key pairs, exchanged only their public keys and inspected the fingerprints. Alice's detached signature verified as a good signature, although GnuPG warned that her key was not certified, which showed the difference between a valid signature and a trusted identity. A message encrypted for Bob was decrypted only with Bob's private key, and the signed-and-encrypted message showed both the content and the signature status. In S/MIME, a lab CA issued certificates for Alice and Bob; the signed message verified successfully, and the encrypted message was decrypted with bob.key. Changing a single character caused a BAD signature in GnuPG and a digest failure in OpenSSL, proving integrity protection. Verifying without the issuing CA failed with "unable to get local issuer certificate", a trust failure rather than a content failure. Both systems use hybrid encryption and digital signatures; PGP relies on users verifying fingerprints, while S/MIME relies on a CA hierarchy and certificate management.

*(176 words)*
