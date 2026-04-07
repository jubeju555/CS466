#!/bin/bash
for script in fs3 fs4; do
    echo ""
    echo "===== Testing $script ====="
    timeout 20 python3 ${script}.py --mode local 2>&1 | tail -20
    ec=$?
    echo "Exit code: $ec"
done
