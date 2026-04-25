#!/bin/bash
python3 -c "
import sys, subprocess, threading
p = subprocess.Popen(['/opt/homebrew/bin/stockfish'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
def relay(src, dst, inject=None):
    try:
        for line in src:
            dst.write(line); dst.flush()
            if inject and line.strip() == 'uci':
                dst.write(inject); dst.flush()
    except: pass
threading.Thread(target=relay, args=(sys.stdin, p.stdin, 'setoption name Skill Level value 1\n'), daemon=True).start()
relay(p.stdout, sys.stdout)
"
