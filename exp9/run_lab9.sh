#!/usr/bin/env bash
# run_lab9.sh - Lab 9: Building and Securing a Two-Tier PKI with X.509 (Parts A to G).
#
# Runs every command of the lab manual in $HOME/pki-lab, exactly as written, and records each
# command with its real output in exp9/logs/ (used later for the report and screenshots).
# At the end it collects the submission files (no private keys) into exp9/submission/.
#
# usage (Ubuntu / WSL):   bash exp9/run_lab9.sh
# needs: openssl nginx curl tshark, and sudo (for /etc/hosts and for capturing on lo)
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
LOGS=$HERE/logs
export PKI=$HOME/pki-lab
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
PROMPT="$(whoami)@$(hostname):~/pki-lab\$"
mkdir -p "$LOGS"
rm -f "$LOGS"/*.log

LOG=/dev/null
step() { LOG="$LOGS/$1.log"; : > "$LOG"; echo "=== $1 ==="; }
# run a command in $PKI and log "prompt + command" and its output
# (run inside a pseudo-terminal via `script`, so programs behave exactly as when typed by hand)
run() { echo "$PROMPT $*" | tee -a "$LOG"
        (cd "$PKI" && script -qefc "bash -c $(printf '%q' "$*")" /dev/null < /dev/null) 2>&1 | tr -d '\r' | tee -a "$LOG"
        echo >> "$LOG"; }
# show a file being created: log a heredoc command and write the file
write_file() { local path=$1; local body; body=$(cat)
  { echo "$PROMPT cat > $path <<'EOF'"; echo "$body"; echo "EOF"; echo; } >> "$LOG"
  printf '%s\n' "$body" > "$PKI/$path"; }
errlog_mark() { wc -l < "$PKI/nginx/error.log" 2>/dev/null || echo 0; }
errlog_since() { run "tail -n +$(( $1 + 1 )) nginx/error.log"; }
nginx_reload() { run 'nginx -p $PKI/nginx -c $PKI/nginx/nginx.conf -s reload'; sleep 1.5; }

# ---------------------------------------------------------------- pre-flight checks
for t in openssl nginx curl tshark; do
  command -v $t >/dev/null || { echo "missing: $t  ->  sudo apt install -y openssl nginx curl wireshark tshark"; exit 1; }
done
if ! getent hosts server.lab.local >/dev/null; then
  echo "adding server.lab.local to /etc/hosts (sudo)"
  echo '127.0.0.1 server.lab.local' | $SUDO tee -a /etc/hosts >/dev/null
fi
[ -n "$SUDO" ] && { echo "sudo is needed for tshark on lo:"; sudo -v || exit 1; }
# stop anything left over from an earlier run
nginx -p "$PKI/nginx" -c "$PKI/nginx/nginx.conf" -s stop >/dev/null 2>&1
pkill -f "openssl ocsp -index" >/dev/null 2>&1
if [ -d "$PKI" ]; then mv "$PKI" "$PKI.old.$(date +%s)"; fi
mkdir -p "$PKI"

# ---------------------------------------------------------------- 0. environment and setup
step 00_environment
run "openssl version"
run "nginx -v"
run "curl --version | head -1"
run "tshark --version | head -1"
run "lsb_release -d 2>/dev/null || grep PRETTY_NAME /etc/os-release; uname -r"
run "grep server.lab.local /etc/hosts"

step 01_setup
mkdir -p "$PKI"
run 'export PKI=$HOME/pki-lab'
run 'mkdir -p $PKI/{root,intermediate,server,client,nginx,captures}'
run 'cd $PKI && mkdir -p root/{certs,crl,newcerts,private}'
run 'mkdir -p intermediate/{certs,crl,csr,newcerts,private}'
run 'chmod 700 root/private intermediate/private'
run 'touch root/index.txt intermediate/index.txt'
run 'echo 1000 > root/serial'
run 'echo 1000 > intermediate/serial'
run 'echo 1000 > root/crlnumber'
run 'echo 1000 > intermediate/crlnumber'
run 'ls -R root intermediate | head -20'

# ---------------------------------------------------------------- Part A: Root CA
step A1_root_config
write_file root/openssl.cnf <<'CNF'
[ ca ]
default_ca = CA_default

[ CA_default ]
dir               = $ENV::PKI/root
certs             = $dir/certs
crl_dir           = $dir/crl
new_certs_dir     = $dir/newcerts
database          = $dir/index.txt
serial            = $dir/serial
crlnumber         = $dir/crlnumber
private_key       = $dir/private/root.key.pem
certificate       = $dir/certs/root.cert.pem
crl               = $dir/crl/root.crl.pem
default_md        = sha256
default_days      = 365
default_crl_days  = 30
policy            = policy_loose
unique_subject    = no
copy_extensions   = none

[ policy_loose ]
countryName             = optional
organizationName        = optional
organizationalUnitName  = optional
commonName              = supplied

[ req ]
default_md          = sha256
distinguished_name  = req_dn
prompt              = no

[ req_dn ]
CN = placeholder

[ v3_root_ca ]
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints       = critical, CA:true
keyUsage               = critical, keyCertSign, cRLSign

[ v3_intermediate_ca ]
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints       = critical, CA:true, pathlen:0
keyUsage               = critical, keyCertSign, cRLSign

[ crl_ext ]
authorityKeyIdentifier = keyid:always
CNF

step A2_root_key_cert
run 'openssl genrsa -out root/private/root.key.pem 4096'
run 'chmod 400 root/private/root.key.pem'
run "openssl req -config root/openssl.cnf -new -x509 -days 3650 -sha256 \\
  -extensions v3_root_ca \\
  -key root/private/root.key.pem \\
  -subj '/O=CSE Lab/CN=CSE Lab Root CA' \\
  -out root/certs/root.cert.pem"
run 'ls -l root/private root/certs'

step A3_root_inspect
run 'openssl x509 -in root/certs/root.cert.pem -noout -text'

# ---------------------------------------------------------------- Part B: Intermediate CA
step B1_intermediate_config
write_file intermediate/openssl.cnf <<'CNF'
[ ca ]
default_ca = CA_default

[ CA_default ]
dir               = $ENV::PKI/intermediate
certs             = $dir/certs
crl_dir           = $dir/crl
new_certs_dir     = $dir/newcerts
database          = $dir/index.txt
serial            = $dir/serial
crlnumber         = $dir/crlnumber
private_key       = $dir/private/intermediate.key.pem
certificate       = $dir/certs/intermediate.cert.pem
crl               = $dir/crl/intermediate.crl.pem
default_md        = sha256
default_days      = 365
default_crl_days  = 30
policy            = policy_loose
unique_subject    = no
copy_extensions   = none

[ policy_loose ]
countryName             = optional
organizationName        = optional
organizationalUnitName  = optional
commonName              = supplied

[ req ]
default_md          = sha256
distinguished_name  = req_dn
prompt              = no

[ req_dn ]
CN = placeholder

[ server_cert ]
basicConstraints       = CA:FALSE
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid,issuer:always
keyUsage               = critical, digitalSignature, keyEncipherment
extendedKeyUsage       = serverAuth
subjectAltName         = @alt_names
authorityInfoAccess    = OCSP;URI:http://127.0.0.1:2560

[ client_cert ]
basicConstraints       = CA:FALSE
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid,issuer:always
keyUsage               = critical, digitalSignature
extendedKeyUsage       = clientAuth
authorityInfoAccess    = OCSP;URI:http://127.0.0.1:2560

[ alt_names ]
DNS.1 = server.lab.local
DNS.2 = localhost
IP.1  = 127.0.0.1

[ crl_ext ]
authorityKeyIdentifier = keyid:always
CNF

step B2_intermediate_key_csr_sign
run 'openssl genrsa -out intermediate/private/intermediate.key.pem 4096'
run 'chmod 400 intermediate/private/intermediate.key.pem'
run "openssl req -config intermediate/openssl.cnf -new -sha256 \\
  -key intermediate/private/intermediate.key.pem \\
  -subj '/O=CSE Lab/CN=CSE Lab Intermediate CA' \\
  -out intermediate/csr/intermediate.csr.pem"
run "openssl ca -batch -config root/openssl.cnf -extensions v3_intermediate_ca \\
  -days 1825 -notext -md sha256 \\
  -in intermediate/csr/intermediate.csr.pem \\
  -out intermediate/certs/intermediate.cert.pem"

step B3_chain_verify
run "cat intermediate/certs/intermediate.cert.pem root/certs/root.cert.pem \\
  > intermediate/certs/ca-chain.cert.pem"
run 'openssl verify -CAfile root/certs/root.cert.pem intermediate/certs/intermediate.cert.pem'
run 'cat root/index.txt'

step B4_intermediate_inspect
run 'openssl x509 -in intermediate/certs/intermediate.cert.pem -noout -text'

# ---------------------------------------------------------------- Part C: server and client certificates
step C1_server_cert
run 'openssl genrsa -out server/server.key.pem 2048'
run "openssl req -new -key server/server.key.pem \\
  -subj '/O=CSE Lab/CN=server.lab.local' -out server/server.csr.pem"
run "openssl ca -batch -config intermediate/openssl.cnf -extensions server_cert \\
  -days 365 -notext -md sha256 \\
  -in server/server.csr.pem -out server/server.cert.pem"
run 'cat server/server.cert.pem intermediate/certs/intermediate.cert.pem > server/server.fullchain.pem'

step C2_client_certs
run 'for u in alice bob; do
  openssl genrsa -out client/$u.key.pem 2048
  openssl req -new -key client/$u.key.pem \
    -subj "/O=CSE Lab/CN=$u" -out client/$u.csr.pem
  openssl ca -batch -config intermediate/openssl.cnf -extensions client_cert \
    -days 365 -notext -md sha256 \
    -in client/$u.csr.pem -out client/$u.cert.pem
done'

step C3_verify
run 'openssl verify -CAfile intermediate/certs/ca-chain.cert.pem server/server.cert.pem'
run 'openssl verify -CAfile intermediate/certs/ca-chain.cert.pem client/alice.cert.pem'
run 'openssl verify -CAfile intermediate/certs/ca-chain.cert.pem -purpose sslclient client/alice.cert.pem'

step C4_task
run 'cat intermediate/index.txt'
run 'ls intermediate/newcerts'
run 'openssl verify -CAfile intermediate/certs/ca-chain.cert.pem -purpose sslserver client/alice.cert.pem'
run 'openssl x509 -in client/alice.cert.pem -noout -ext extendedKeyUsage,keyUsage'
run 'openssl x509 -in server/server.cert.pem -noout -subject -ext subjectAltName,extendedKeyUsage'

step C5_server_inspect
run 'openssl x509 -in server/server.cert.pem -noout -text'

# Task B demonstrations: a certificate signed by a leaf, and the pathlen:0 limit
step B5_task_demos
run 'mkdir -p demo'
run "openssl req -new -newkey rsa:2048 -nodes -keyout demo/evil.key.pem \\
  -subj '/O=Evil/CN=evil' -out demo/evil.csr.pem 2>/dev/null"
run "openssl x509 -req -in demo/evil.csr.pem -CA client/alice.cert.pem -CAkey client/alice.key.pem \\
  -CAcreateserial -days 30 -out demo/evil.cert.pem"
run 'openssl verify -CAfile intermediate/certs/ca-chain.cert.pem -untrusted client/alice.cert.pem demo/evil.cert.pem'
run "printf 'basicConstraints=critical,CA:true\nkeyUsage=critical,keyCertSign,cRLSign\n' > demo/subca.ext"
run "openssl req -new -newkey rsa:2048 -nodes -keyout demo/subca.key.pem \\
  -subj '/O=CSE Lab/CN=Sub CA' -out demo/subca.csr.pem 2>/dev/null"
run "openssl x509 -req -in demo/subca.csr.pem -CA intermediate/certs/intermediate.cert.pem \\
  -CAkey intermediate/private/intermediate.key.pem -CAcreateserial -days 30 \\
  -extfile demo/subca.ext -out demo/subca.cert.pem"
run "openssl req -new -newkey rsa:2048 -nodes -keyout demo/leaf.key.pem \\
  -subj '/O=CSE Lab/CN=leaf' -out demo/leaf.csr.pem 2>/dev/null"
run "openssl x509 -req -in demo/leaf.csr.pem -CA demo/subca.cert.pem -CAkey demo/subca.key.pem \\
  -CAcreateserial -days 30 -out demo/leaf.cert.pem"
run 'cat demo/subca.cert.pem intermediate/certs/intermediate.cert.pem > demo/sub+intermediate.pem'
run 'openssl verify -CAfile root/certs/root.cert.pem -untrusted demo/sub+intermediate.pem demo/leaf.cert.pem'

# ---------------------------------------------------------------- Part D: mutual TLS with nginx
step D1_nginx_config
write_file nginx/nginx.conf <<CNF
pid $PKI/nginx/nginx.pid;
error_log $PKI/nginx/error.log info;
events {}
http {
  access_log $PKI/nginx/access.log;
  server {
    listen 8443 ssl;
    server_name server.lab.local;

    ssl_certificate         $PKI/server/server.fullchain.pem;
    ssl_certificate_key     $PKI/server/server.key.pem;
    ssl_protocols           TLSv1.2 TLSv1.3;

    ssl_client_certificate  $PKI/intermediate/certs/ca-chain.cert.pem;
    ssl_verify_client       on;
    ssl_verify_depth        2;

    location / {
      return 200 'Hello \$ssl_client_s_dn | verify=\$ssl_client_verify | proto=\$ssl_protocol';
    }
  }
}
CNF
run 'echo $HOME'
run 'nginx -p $PKI/nginx -c $PKI/nginx/nginx.conf'
sleep 1.5
run 'ss -ltnp 2>/dev/null | grep 8443 || netstat -ltn | grep 8443'

step D2_test
run "curl --cacert intermediate/certs/ca-chain.cert.pem \\
  --cert client/alice.cert.pem --key client/alice.key.pem \\
  https://server.lab.local:8443/"
run 'echo'
M=$(errlog_mark)
run 'curl --cacert intermediate/certs/ca-chain.cert.pem https://server.lab.local:8443/'
run 'curl -i --cacert intermediate/certs/ca-chain.cert.pem https://server.lab.local:8443/'
errlog_since "$M"
run 'tail -n 3 nginx/access.log'

step D3_s_client
run "openssl s_client -connect server.lab.local:8443 -CAfile intermediate/certs/ca-chain.cert.pem \\
  -cert client/alice.cert.pem -key client/alice.key.pem -showcerts < /dev/null"

# ---------------------------------------------------------------- Part E: revocation
step E1_revoke_crl
run 'openssl ca -config intermediate/openssl.cnf -revoke client/bob.cert.pem -crl_reason keyCompromise'
run 'openssl ca -config intermediate/openssl.cnf -gencrl -out intermediate/crl/intermediate.crl.pem'
run 'openssl ca -config root/openssl.cnf -gencrl -out root/crl/root.crl.pem'
run 'cat intermediate/crl/intermediate.crl.pem root/crl/root.crl.pem > intermediate/crl/combined.crl.pem'
run 'openssl crl -in intermediate/crl/intermediate.crl.pem -noout -text'
run 'openssl crl -in root/crl/root.crl.pem -noout -text'
run 'cat intermediate/index.txt'

step E1b_verify_crl
run "openssl verify -crl_check -CAfile intermediate/certs/ca-chain.cert.pem \\
  -CRLfile intermediate/crl/combined.crl.pem client/bob.cert.pem"
run "openssl verify -crl_check -CAfile intermediate/certs/ca-chain.cert.pem \\
  -CRLfile intermediate/crl/combined.crl.pem client/alice.cert.pem"

step E2_nginx_crl
run "sed -i 's#^    ssl_verify_depth        2;#    ssl_verify_depth        2;\\n    ssl_crl                 $PKI/intermediate/crl/combined.crl.pem;#' nginx/nginx.conf"
run 'grep -n ssl_ nginx/nginx.conf'
nginx_reload
M=$(errlog_mark)
run "curl --cacert intermediate/certs/ca-chain.cert.pem \\
  --cert client/alice.cert.pem --key client/alice.key.pem https://server.lab.local:8443/"
run 'echo'
run "curl --cacert intermediate/certs/ca-chain.cert.pem \\
  --cert client/bob.cert.pem --key client/bob.key.pem https://server.lab.local:8443/"
errlog_since "$M"

step E2b_without_root_crl
run 'cp intermediate/crl/combined.crl.pem intermediate/crl/combined.crl.pem.bak'
run 'cp intermediate/crl/intermediate.crl.pem intermediate/crl/combined.crl.pem'
nginx_reload
M=$(errlog_mark)
run "curl --cacert intermediate/certs/ca-chain.cert.pem \\
  --cert client/alice.cert.pem --key client/alice.key.pem https://server.lab.local:8443/"
errlog_since "$M"
run 'mv intermediate/crl/combined.crl.pem.bak intermediate/crl/combined.crl.pem'
nginx_reload
run "curl --cacert intermediate/certs/ca-chain.cert.pem \\
  --cert client/alice.cert.pem --key client/alice.key.pem https://server.lab.local:8443/"
run 'echo'

step E3_ocsp
# Terminal 2: the OCSP responder (runs in the background; its output goes to E3_ocsp_responder.log)
echo "$PROMPT export PKI=\$HOME/pki-lab; cd \$PKI" > "$LOGS/E3_ocsp_responder.log"
echo "$PROMPT openssl ocsp -index intermediate/index.txt -port 2560 \\
  -rsigner intermediate/certs/intermediate.cert.pem \\
  -rkey intermediate/private/intermediate.key.pem \\
  -CA intermediate/certs/ca-chain.cert.pem -text" >> "$LOGS/E3_ocsp_responder.log"
(cd "$PKI" && exec openssl ocsp -index intermediate/index.txt -port 2560 \
  -rsigner intermediate/certs/intermediate.cert.pem \
  -rkey intermediate/private/intermediate.key.pem \
  -CA intermediate/certs/ca-chain.cert.pem -text >> "$LOGS/E3_ocsp_responder.log" 2>&1) &
OCSP_PID=$!
sleep 2
run "openssl ocsp -issuer intermediate/certs/intermediate.cert.pem \\
  -cert client/alice.cert.pem -url http://127.0.0.1:2560 \\
  -CAfile intermediate/certs/ca-chain.cert.pem -resp_text"
run "openssl ocsp -issuer intermediate/certs/intermediate.cert.pem \\
  -cert client/bob.cert.pem -url http://127.0.0.1:2560 \\
  -CAfile intermediate/certs/ca-chain.cert.pem -resp_text"
run 'openssl x509 -in server/server.cert.pem -noout -ext authorityInfoAccess'
kill $OCSP_PID 2>/dev/null; wait $OCSP_PID 2>/dev/null

# ---------------------------------------------------------------- Part F: TLS handshake captures
capture() {  # capture <file> <curl command>   (tshark on lo, filter tcp port 8443, in "terminal 2")
  local out=$1; shift
  local tlog=$LOGS/.tshark.$$
  local term2=$LOGS/${LOG##*/}; term2=${term2%.log}_tshark_terminal.log
  echo "$PROMPT ${SUDO:+$SUDO }tshark -i lo -f \"tcp port 8443\" -w captures/$out" > "$term2"
  $SUDO rm -f "/tmp/$out"
  $SUDO tshark -i lo -f "tcp port 8443" -w "/tmp/$out" > "$tlog" 2>&1 &
  local tpid=$!
  for _ in $(seq 1 40); do grep -q "Capturing on" "$tlog" 2>/dev/null && break; sleep 0.25; done
  sleep 1
  run "$*"
  sleep 1.5
  $SUDO kill -INT "$tpid" 2>/dev/null
  wait $tpid 2>/dev/null
  $SUDO cp "/tmp/$out" "$PKI/captures/$out"
  $SUDO chown "$(id -u):$(id -g)" "$PKI/captures/$out"
  grep -v "Running as user" "$tlog" >> "$term2"; rm -f "$tlog"
}

step F1_tls12
capture tls12.pcapng "curl --tlsv1.2 --tls-max 1.2 --cacert intermediate/certs/ca-chain.cert.pem \\
  --cert client/alice.cert.pem --key client/alice.key.pem https://server.lab.local:8443/"
run 'tshark -r captures/tls12.pcapng -Y tls.handshake'
run "tshark -r captures/tls12.pcapng -Y 'tls.handshake.type == 1' -V | grep -E 'Server Name:|Cipher Suites \\(|Cipher Suites Length' "
run "tshark -r captures/tls12.pcapng -Y 'tls.handshake.type == 1' -T fields -e tls.handshake.ciphersuite | tr ',' '\\n' | head -5"
run "tshark -r captures/tls12.pcapng -Y 'tls.handshake.type == 2' -V | grep -E 'Handshake Type: Server Hello|Cipher Suite:'"
run "tshark -r captures/tls12.pcapng -Y 'tls.handshake.type == 11'"
run "tshark -r captures/tls12.pcapng -Y 'tls.handshake.type == 11' -V | grep -E 'Handshake Type|Certificate Length|rdnSequence|utcTime|dNSName|iPAddress|KeyPurposeId|accessLocation|uniformResourceIdentifier'"
run "tshark -r captures/tls12.pcapng -Y 'tls.handshake.type == 13 || tls.handshake.type == 15'"
run "tshark -r captures/tls12.pcapng -Y 'tls.handshake.type == 13' -V | grep -E 'Handshake Type|Distinguished Name|rdnSequence'"
run "tshark -r captures/tls12.pcapng -Y 'tls.handshake.type == 15' -V | grep -E 'Handshake Type|Signature Algorithm|Signature length'"

step F2_tls13
run 'export SSLKEYLOGFILE=$PKI/captures/keys.log'
export SSLKEYLOGFILE=$PKI/captures/keys.log
capture tls13.pcapng "curl --tlsv1.3 --cacert intermediate/certs/ca-chain.cert.pem \\
  --cert client/alice.cert.pem --key client/alice.key.pem https://server.lab.local:8443/"
unset SSLKEYLOGFILE
run 'cut -d" " -f1 captures/keys.log'
run 'tshark -r captures/tls13.pcapng -Y tls.handshake'
run 'tshark -r captures/tls13.pcapng -Y tls'
run "tshark -r captures/tls13.pcapng -Y 'tls.handshake.type == 11'"
run "tshark -r captures/tls13.pcapng -Y 'tls.handshake.type == 2' -V | grep -E 'Cipher Suite:|Supported Version:|Group:'"

step F3_tls13_decrypted
run 'tshark -r captures/tls13.pcapng -o tls.keylog_file:captures/keys.log -Y tls.handshake'
run "tshark -r captures/tls13.pcapng -o tls.keylog_file:captures/keys.log -Y 'tls.handshake.type == 11'"
run "tshark -r captures/tls13.pcapng -o tls.keylog_file:captures/keys.log -Y 'tls.handshake.type == 11' -V | grep -E 'Handshake Type|rdnSequence'"
run "tshark -r captures/tls13.pcapng -o tls.keylog_file:captures/keys.log -Y 'tls.handshake.type == 13 || tls.handshake.type == 15'"
run 'ls -l captures'

# ---------------------------------------------------------------- Part G: failure scenarios
URL=https://server.lab.local:8443/
CHAIN=intermediate/certs/ca-chain.cert.pem

step G1_expired
run 'openssl genrsa -out client/eve.key.pem 2048'
run "openssl req -new -key client/eve.key.pem -subj '/O=CSE Lab/CN=eve' -out client/eve.csr.pem"
run "openssl ca -batch -config intermediate/openssl.cnf -extensions client_cert \\
  -startdate 20240101000000Z -enddate 20240102000000Z -notext -md sha256 \\
  -in client/eve.csr.pem -out client/eve.cert.pem"
M=$(errlog_mark)
run "curl --cacert $CHAIN --cert client/eve.cert.pem --key client/eve.key.pem $URL"
errlog_since "$M"
run "openssl verify -CAfile $CHAIN client/eve.cert.pem"

step G2_untrusted
run "openssl req -x509 -newkey rsa:2048 -nodes -keyout client/mallory.key.pem -out client/mallory.cert.pem \\
  -days 30 -subj '/O=Evil/CN=mallory'"
M=$(errlog_mark)
run "curl --cacert $CHAIN --cert client/mallory.cert.pem --key client/mallory.key.pem $URL"
errlog_since "$M"
run "openssl verify -CAfile $CHAIN client/mallory.cert.pem"

step G3_wrong_purpose
M=$(errlog_mark)
run "curl --cacert $CHAIN --cert server/server.cert.pem --key server/server.key.pem $URL"
errlog_since "$M"
run "openssl verify -CAfile $CHAIN -purpose sslclient server/server.cert.pem"

step G4_hostname
M=$(errlog_mark)
run "curl --resolve wrong.lab.local:8443:127.0.0.1 --cacert $CHAIN \\
  --cert client/alice.cert.pem --key client/alice.key.pem https://wrong.lab.local:8443/"
errlog_since "$M"
run "openssl s_client -connect 127.0.0.1:8443 -servername wrong.lab.local -verify_hostname wrong.lab.local \\
  -CAfile $CHAIN -cert client/alice.cert.pem -key client/alice.key.pem < /dev/null 2>&1 | grep -E 'verify error|Verify return code|Verification'"

step G5_missing_intermediate
run "sed -i 's#server/server.fullchain.pem;#server/server.cert.pem;#' nginx/nginx.conf"
run 'grep -n "ssl_certificate " nginx/nginx.conf'
nginx_reload
run "curl --cacert $CHAIN --cert client/alice.cert.pem --key client/alice.key.pem $URL"
run 'echo'
M=$(errlog_mark)
run "curl --cacert root/certs/root.cert.pem --cert client/alice.cert.pem --key client/alice.key.pem $URL"
errlog_since "$M"
run "openssl s_client -connect server.lab.local:8443 -CAfile root/certs/root.cert.pem \\
  -cert client/alice.cert.pem -key client/alice.key.pem < /dev/null 2>&1 | grep -E 'depth|verify error|Verify return code|Certificate chain| s:| i:'"
run "sed -i 's#server/server.cert.pem;#server/server.fullchain.pem;#' nginx/nginx.conf"
run 'grep -n "ssl_certificate " nginx/nginx.conf'
nginx_reload
run "curl --cacert root/certs/root.cert.pem --cert client/alice.cert.pem --key client/alice.key.pem $URL"
run 'echo'

step G6_revoked
M=$(errlog_mark)
run "curl --cacert $CHAIN --cert client/bob.cert.pem --key client/bob.key.pem $URL"
errlog_since "$M"
run "openssl verify -crl_check -CAfile $CHAIN -CRLfile intermediate/crl/combined.crl.pem client/bob.cert.pem"

step G7_errorlog_summary
run "grep -E 'verify error|no required SSL certificate' nginx/error.log"

# ---------------------------------------------------------------- stop servers, collect submission
run 'nginx -p $PKI/nginx -c $PKI/nginx/nginx.conf -s stop'
SUB=$HERE/submission
rm -rf "$SUB"; mkdir -p "$SUB"
(cd "$PKI" && cp --parents root/openssl.cnf intermediate/openssl.cnf \
   root/certs/root.cert.pem intermediate/certs/intermediate.cert.pem intermediate/certs/ca-chain.cert.pem \
   server/server.cert.pem server/server.fullchain.pem \
   client/alice.cert.pem client/bob.cert.pem client/eve.cert.pem client/mallory.cert.pem \
   root/crl/root.crl.pem intermediate/crl/intermediate.crl.pem intermediate/crl/combined.crl.pem \
   root/index.txt intermediate/index.txt nginx/nginx.conf nginx/error.log nginx/access.log \
   captures/tls12.pcapng captures/tls13.pcapng captures/keys.log "$SUB"/)
grep -E 'verify error|no required SSL certificate|unable to get' "$PKI/nginx/error.log" > "$SUB/nginx/error_log_excerpts.txt"
# safety: there must be no private keys in the submission
if find "$SUB" -name '*.key.pem' | grep -q .; then echo "ERROR: private key found in submission"; exit 1; fi
echo "done - logs in $LOGS, submission files in $SUB (no private keys)"
