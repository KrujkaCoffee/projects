from __future__ import print_function

import os
import re
import shutil
import tempfile

p = "/root/find_bad_length.py"

with open(p, "r") as f:
    s = f.read()

pattern = r"(?m)^([ \t]*)ip = pkt\[16:\][ \t]*$"

ip_lines = [
    "ip = pkt[16:]",
    "if len(ip) < 20:",
    "    raise RuntimeError('Incomplete IPv4 header')",
    "if (ord(ip[0]) >> 4) != 4:",
    "    continue",
    "if ord(ip[9]) != 6:",
    "    continue",
    "ip_hlen = (ord(ip[0]) & 15) * 4",
    "ip_len = struct.unpack('!H', ip[2:4])[0]",
    "if ip_hlen < 20 or ip_len < ip_hlen + 20:",
    "    raise RuntimeError('Invalid IPv4/TCP length')",
    "if len(ip) < ip_len:",
    "    raise RuntimeError('Truncated IPv4 packet')",
    "if struct.unpack('!H', ip[6:8])[0] & 0x3fff:",
    "    raise RuntimeError('Fragmented IPv4 is not supported')",
    "ip = ip[:ip_len]",
]

def replace_ip(m):
    return "\n".join(m.group(1) + line for line in ip_lines)

s, count = re.subn(pattern, replace_ip, s)

if count != 1:
    raise SystemExit("IP block not found uniquely; file unchanged")

# Replace the entire broken try/except block.
anchor = s.find("body = stream[body_start:body_end]")
start = s.find("\ntry:\n", anchor) if anchor >= 0 else -1
end = s.find('\nfacts = data.get("facts")', start) if start >= 0 else -1

if start < 0 or end < 0:
    raise SystemExit("JSON block not found; file unchanged")

fixed = '''
try:
    decoded = body.decode("utf-8")
    data = json.loads(decoded)
except UnicodeDecodeError as e:
    raise RuntimeError("Strict UTF-8 failed at byte %d" % e.start)
except ValueError:
    raise RuntimeError("JSON parsing failed; body not printed")

print("UTF-8: OK")
print("JSON: OK")

if not isinstance(data, dict):
    raise RuntimeError("Expected a JSON object")
'''

s = s[:start] + fixed + s[end:]

compile(s, p, "exec")

fd, tmp = tempfile.mkstemp(
    prefix="find_bad_length_",
    suffix=".py",
    dir=os.path.dirname(p)
)

try:
    with os.fdopen(fd, "w") as f:
        f.write(s)

    backup = tmp + ".bak"
    shutil.copyfile(p, backup)
    os.chmod(backup, 0o600)

    os.rename(tmp, p)

except Exception:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise

print("Patched; syntax OK")
print("Backup:", backup)