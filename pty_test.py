import pty, os, subprocess, time

master, slave = pty.openpty()
cmd = ["python3", "-c", "import sys, time; sys.stdout.write('chunk1\\n'); time.sleep(1); sys.stdout.write('chunk2\\n'); time.sleep(1)"]

p = subprocess.Popen(cmd, stdout=slave, stderr=slave, stdin=subprocess.DEVNULL)
os.close(slave)

with os.fdopen(master, 'r') as f:
    while True:
        try:
            char = f.read(1)
            if not char: break
            print(f"Read: {repr(char)}")
        except OSError:
            break
