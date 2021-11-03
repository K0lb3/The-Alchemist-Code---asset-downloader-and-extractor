import sys
from lib.version import extract_version, get_version_consts_fp
print(sys.argv)

if len(sys.argv) != 3:
    ver = input("version (global/japan):\t")
    apk = input("apk_path:\t")
else:
    ver = sys.argv[1]
    apk = sys.argv[2]

class F:
    pass
F.name = ver
settings_fp = get_version_consts_fp(F)
with open(apk, "rb") as f:
    apk_data = f.read()
network_ver, shared_key = extract_version(apk_data)

with open(settings_fp, "wb") as f:
    f.write(network_ver.encode("utf8"))
    f.write(b"\r\n")
    f.write(shared_key)
print("Network Version:", network_ver)
print("Shared Key:", shared_key)