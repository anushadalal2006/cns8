# Lab 9 — Answers to handwrite

**Name:** Anusha Dalal **UID:** 2024300032

All values below are from your own run (29 Oct 2026).

---

## Task A — Root CA

**Recorded values**
- Serial number: **04:6d:bf:53:f3:58:1f:56:a2:96:8f:58:d6:bb:62:c4:a1:27:47:0a** (a random 20-byte value; OpenSSL 3 makes it random for self-signed certificates)
- Validity: **10 years (3650 days)**: **Oct 29 10:24:35 2026 GMT** to **Oct 26 10:24:35 2036 GMT**
- Signature algorithm: **sha256WithRSAEncryption**
- Key size: **RSA 4096 bits**
- Extensions:
  - Subject Key Identifier (hash of the public key)
  - Authority Key Identifier (equals the SKI, because the root signs itself)
  - Basic Constraints: **critical, CA:TRUE**
  - Key Usage: **critical, Certificate Sign, CRL Sign**

**Why is basicConstraints critical?** It decides whether a key may sign other certificates, which is the most security-sensitive fact in a certificate. "Critical" forces every program to obey it or reject the certificate, so no software can ignore it and treat a normal certificate as a CA (or the reverse). RFC 5280 requires it to be critical in CA certificates.

**Why is a Root CA self-signed (issuer = subject)?** It is the top of the chain, so nobody higher can sign it. Its signature only makes it a well-formed certificate; trust in it comes **out of band** (installed in a trust store, or passed with `--cacert`). That is also why its AKI equals its SKI.

---

## Task B — Intermediate CA

**Root vs Intermediate**

| | Root CA | Intermediate CA |
|---|---|---|
| Subject | O=CSE Lab, CN=CSE Lab Root CA | O=CSE Lab, CN=CSE Lab Intermediate CA |
| Issuer | itself | CSE Lab Root CA |
| Signed with | its own key | the Root's key |
| Validity | 10 years | 5 years (1825 days) |
| Key | RSA 4096 | RSA 4096 |
| Serial | random 20 bytes | 0x1000 (from the Root's serial file) |
| Basic Constraints | critical, CA:TRUE | critical, CA:TRUE, **pathlen:0** |
| Key Usage | critical, keyCertSign, cRLSign | critical, keyCertSign, cRLSign |
| AKI | = its own SKI | = the **Root's** SKI |

**What does pathlen:0 do?** It allows **zero** further CA certificates below the Intermediate, so it can sign only end-entity (leaf) certificates. If the Intermediate key is stolen, the thief still cannot create a valid sub-CA. My test: a Sub CA signed by the Intermediate, then a leaf signed by that Sub CA → **error 25: path length constraint exceeded**.

**What if a certificate is issued from a leaf?** It is rejected. A leaf has **CA:FALSE** and its key usage has no **keyCertSign**. My test (a certificate signed with Alice's key) → **error 79: invalid CA certificate** and **error 32: key usage does not include certificate signing**.

---

## Task C — Server and client certificates

**1. index.txt columns** (TAB-separated):
1. **Status:** V = valid, R = revoked, E = expired
2. **Expiry** date-time, YYMMDDHHMMSSZ (UTC)
3. **Revocation** date and reason (empty while valid)
4. **Serial** number in hex (1000 = server, 1001 = alice, 1002 = bob; same as the files in newcerts/)
5. File name (always "unknown")
6. **Subject** DN (e.g. /O=CSE Lab/CN=alice)

**2. Alice with `-purpose sslserver`:** fails with **error 26: unsuitable certificate purpose**. Cause: the **Extended Key Usage** extension says only *TLS Web Client Authentication* (clientAuth), so it is not valid as a server certificate.

**3. Why SAN when CN has the hostname?** The CN is an old free-text field. Modern clients (RFC 6125/2818, browsers since ~2017) check host names **only in the Subject Alternative Name**, a structured list that can hold several DNS names and IP addresses. Our SAN covers server.lab.local, localhost and 127.0.0.1, so one certificate works for all three.

---

## Task D — Mutual TLS with nginx

**1. Outputs and status.**
- Alice: `Hello CN=alice,O=CSE Lab | verify=SUCCESS | proto=TLSv1.3`
- No certificate: **HTTP 400 Bad Request**, "No required SSL certificate was sent". The TLS handshake itself completes; then nginx, with `ssl_verify_client on`, sees that no client certificate was sent and refuses the request with 400.

**2. What identifies the client?** The variable **`$ssl_client_s_dn`** (printed as CN=alice,O=CSE Lab). In error.log a missing certificate appears as *"client sent no required SSL certificate"* and a bad one as *"client SSL certificate verify error: (N:reason)"*. (The default access.log does not show the DN.)

**3. Why ssl_client_certificate and ssl_verify_depth 2?** `ssl_client_certificate` gives nginx the **trusted CA chain** to check client certificates against; without it every client certificate would fail. `ssl_verify_depth` is the longest chain nginx will follow: client (0) → Intermediate (1) → Root (2), so 2 fits our chain.

---

## Task E — Revocation

**1. Status.**
- Alice: **good**
- Bob: **revoked**, revocation time **Oct 29 10:24:42 2026 GMT**, reason **keyCompromise**

**2. CRL vs OCSP**

| | CRL | OCSP |
|---|---|---|
| Freshness | Only as new as the last download (valid until Next Update, 30 days here) | Near real time (answers from the live database) |
| Size | Grows with every revoked certificate | One small request and response per certificate |
| Privacy | Good: the CA doesn't learn which certificate you check | Weak: the responder sees which certificate (site) you check |
| Latency | One download, then local look-ups | Extra round trip during connection (unless stapled) |
| Failure | nginx **hard-fails** if the CRL is missing (error 3) | Browsers usually **soft-fail** if the responder is down |

**3. OCSP stapling.** The **server** fetches a signed, time-stamped OCSP response for its own certificate and attaches it to the TLS handshake. Clients don't contact the CA, which fixes OCSP's **privacy leak**, **extra latency** and **dependence on the responder** being up. It can't be forged, because the CA signs it.

**4. Where is the OCSP URL?** In the **Authority Information Access** extension: `OCSP - URI:http://127.0.0.1:2560`.

---

## Task F — TLS handshake analysis

**1. TLS 1.2 vs TLS 1.3**

| | TLS 1.2 | TLS 1.3 |
|---|---|---|
| Round trips before data | **2 RTT** | **1 RTT** |
| Server certificate visible? | **Yes**, plain text | **No**, encrypted (only with keys.log) |
| Client certificate visible? | **Yes**, plain text | **No**, encrypted |
| Key-exchange messages | Separate **ServerKeyExchange** and **ClientKeyExchange** | None: key shares sit in the ClientHello/ServerHello **key_share** extension |
| Cipher suite (my run) | ECDHE-RSA-AES256-GCM-SHA384 (0xc030) | TLS_AES_256_GCM_SHA384 (0x1302), x25519 |

**2. Why is an encrypted client certificate a privacy gain?** The client certificate names a **person** (CN=alice, O=CSE Lab). In TLS 1.2 any observer can read it and **identify and track the user** across sessions. In TLS 1.3 an observer still sees IP addresses, the SNI and packet sizes, but **cannot read either certificate**, so they can't tell who logged in.

**3. Which message proves the client owns the private key?** **CertificateVerify**: the client signs the handshake transcript with its private key, and the server checks it with the public key in the certificate. (A certificate alone proves nothing, since certificates are public.)

**4.** Your Wireshark screenshots go here (they are in the report).

---

## Task G — Failure scenarios (root causes)

1. **Expired client (eve):** the date is outside eve's validity (1–2 Jan 2024) → **10: certificate has expired**.
2. **Untrusted client (Mallory):** her self-signed certificate doesn't chain to our Root. With `ssl_crl` on, nginx reports **3: unable to get certificate CRL** (no CRL for an unknown issuer); `openssl verify` reports **18: self-signed certificate**.
3. **Wrong purpose:** the server certificate's EKU is serverAuth only, not clientAuth → **26: unsuitable certificate purpose**.
4. **Hostname mismatch:** wrong.lab.local is not in the server's SAN → curl (60) "no alternative certificate subject name matches"; s_client **62: hostname mismatch**. The client aborts, so nginx logs no verify error.
5. **Missing intermediate:** the server sends only its leaf. With the full chain in `--cacert` it still works; with only the Root, curl fails "unable to get local issuer certificate" (s_client **20/21**), because the client can't link the leaf to the Root.
6. **Revoked (Bob):** serial 1002 is on the Intermediate's CRL (keyCompromise) and nginx has `ssl_crl` on → **23: certificate revoked**.

---

## Reflection (150–250 words)

**What is the single most common reason real-world TLS deployments fail certificate validation, and how would you prevent it?**

> The most common reason is an **expired certificate**. Every certificate has a fixed lifetime, but renewal is often a manual job that depends on one person remembering it. When the end date passes, every client rejects the certificate at the same moment, so the whole service goes down at once. I reproduced this in Scenario 1: eve's certificate was valid only on 1–2 January 2024, and nginx rejected it with error 10, "certificate has expired". A close second is an incomplete chain (Scenario 5): a server that sends only its leaf certificate works on machines that already have the intermediate, but fails for every other client.
>
> To prevent expiry, I would **automate issuance and renewal** with an ACME client such as certbot, and use short lifetimes so that renewal runs often and any failure is noticed early. I would keep an **inventory** of all certificates and their owners, and set up **monitoring and alerts** at 30, 14 and 7 days before expiry. Finally, before each deployment I would test the server from a clean client that trusts only the Root, for example with `openssl s_client`, to confirm that the full chain is sent and that the certificate is still valid.

*(200 words)*
