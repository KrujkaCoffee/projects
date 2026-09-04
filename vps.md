
# быстрая инфа сервака
```bash
cat /etc/os-release
uname -a

echo "=== NETWORK ==="
ip -br addr
ip route

echo "=== PORTS ==="
ss -lntup

echo "=== TIME ==="
timedatectl

echo "=== FORWARDING ==="
sysctl net.ipv4.ip_forward

echo "=== FIREWALL ==="
command -v ufw >/dev/null && ufw status verbose || true
command -v nft >/dev/null && nft list ruleset || true

echo "=== FAILED SERVICES ==="
systemctl --failed
```

# депы

```shell
sudo apt update

sudo apt install -y \
    openvpn \
    easy-rsa \
    stunnel4 \
    openssl \
    ca-certificates \
    curl \
    tcpdump \
    dnsutils \
    iproute2 \
    netcat-openbsd \
    lsof \
    traceroute
```