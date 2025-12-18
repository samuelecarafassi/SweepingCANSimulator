import cantools
import sys

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <dbc_file>")
    sys.exit(1)

filename = sys.argv[1]


print(f"Loading {filename}...")
db = cantools.database.load_file(filename, strict=False)

# last 2 parameters might be anonymized for industrial secrecy reasons
print("ID | MSG NAME | MSG SENDERS | MSG FREQUENCY")


for msg in db.messages:
    print(hex(msg.frame_id), msg.name, msg.senders, msg.cycle_time)
