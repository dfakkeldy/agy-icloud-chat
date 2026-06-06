import sys, time
for i in range(5):
    sys.stdout.write(f"Chunk {i}\n")
    # intentionally no flush
    time.sleep(1)
