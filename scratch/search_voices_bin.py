import re

with open("weights/kokoro-v1.0/voices.bin", "rb") as f:
    data = f.read()

# Let's search for ASCII sequences of length 3 to 30
strings = re.findall(b"[a-zA-Z0-9_]{3,30}", data)
print(f"Found {len(strings)} ASCII strings.")
# Print the first 100 strings
for s in strings[:100]:
    s_str = s.decode('ascii', errors='ignore')
    if "adam" in s_str.lower() or "voice" in s_str.lower() or "speaker" in s_str.lower() or "am_" in s_str.lower() or "af_" in s_str.lower():
        print("Match:", s_str)
