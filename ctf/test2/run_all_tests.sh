#!/bin/bash
# Comprehensive local test of all format string and exploit challenges

cd /home/jbenjam7/cs466/ctf/test2

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  LOCAL EXPLOIT TEST SUITE - All Challenges                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Results tracking
declare -A results
declare -A flags

# Test 1: fs1 (formatstring1 - random-game, leak + repeat passcode)
echo "[1/6] Testing fs1 - formatstring1 (random-game)"
echo "========================================"
output=$(timeout 10 python3 fs1.py --mode local --binary ./random-game 2>&1)
ec=$?
results["fs1"]=$ec
if echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' > /dev/null; then
    flag=$(echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' | head -1)
    flags["fs1"]="$flag"
    echo "✓ SUCCESS (EC: $ec)"
    echo "  Flag: $flag"
else
    flags["fs1"]="NOT_FOUND"
    echo "✗ FAILED (EC: $ec)"
fi
echo ""

# Test 2: fs2 (formatstring2 - hidden_string, direct string leak)
echo "[2/6] Testing fs2 - formatstring2 (hidden_string)"
echo "========================================"
output=$(timeout 10 python3 fs2.py --mode local --binary ./hidden_string 2>&1)
ec=$?
results["fs2"]=$ec
if echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' > /dev/null; then
    flag=$(echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' | head -1)
    flags["fs2"]="$flag"
    echo "✓ SUCCESS (EC: $ec)"
    echo "  Flag: $flag"
else
    flags["fs2"]="NOT_FOUND"
    echo "✗ FAILED (EC: $ec)"
fi
echo ""

# Test 3: fs3 (formatstring3 - login, global variable write)
echo "[3/6] Testing fs3 - formatstring3 (login)"
echo "========================================"
output=$(timeout 10 python3 fs3.py --mode local 2>&1)
ec=$?
results["fs3"]=$ec
if echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' > /dev/null; then
    flag=$(echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' | head -1)
    flags["fs3"]="$flag"
    echo "✓ SUCCESS (EC: $ec)"
    echo "  Flag: $flag"
elif echo "$output" | grep -q "SUCCESS"; then
    flags["fs3"]="SUCCESS_MARKER"
    echo "✓ SUCCESS (EC: $ec) - Found success marker"
else
    flags["fs3"]="NOT_FOUND"
    echo "✗ FAILED (EC: $ec)"
fi
echo ""

# Test 4: fs4 (formatstring4 - jump, return-address overwrite)
echo "[4/6] Testing fs4 - formatstring4 (jump)"
echo "========================================"
output=$(timeout 10 python3 fs4.py --mode local --binary ./jump 2>&1)
ec=$?
results["fs4"]=$ec
if echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' > /dev/null; then
    flag=$(echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' | head -1)
    flags["fs4"]="$flag"
    echo "✓ SUCCESS (EC: $ec)"
    echo "  Flag: $flag"
elif echo "$output" | grep -q "FS_OK"; then
    flags["fs4"]="FS_OK_MARKER"
    echo "✓ SUCCESS (EC: $ec) - Found FS_OK marker"
else
    flags["fs4"]="NOT_FOUND"
    echo "✗ FAILED (EC: $ec)"
fi
echo ""

# Test 5: fp (framepointer challenge)
echo "[5/6] Testing fp - Framepointer challenge"
echo "========================================"
output=$(timeout 10 python3 fp.py --mode local 2>&1)
ec=$?
results["fp"]=$ec
if echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' > /dev/null; then
    flag=$(echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' | head -1)
    flags["fp"]="$flag"
    echo "✓ SUCCESS (EC: $ec)"
    echo "  Flag: $flag"
else
    flags["fp"]="NOT_FOUND"
    echo "✗ FAILED (EC: $ec)"
fi
echo ""

# Test 6: io (integer-overflow challenge)
echo "[6/6] Testing io - Integer Overflow challenge (challenge-io)"
echo "========================================"
output=$(timeout 10 python3 io.py --mode local --binary ./challenge-io 2>&1)
ec=$?
results["io"]=$ec
if echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' > /dev/null; then
    flag=$(echo "$output" | grep -Eio 'cosc[0-9-]*-flag-\{[^}]+' | head -1)
    flags["io"]="$flag"
    echo "✓ SUCCESS (EC: $ec)"
    echo "  Flag: $flag"
else
    flags["io"]="NOT_FOUND"
    echo "✗ FAILED (EC: $ec)"
fi
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  TEST RESULTS SUMMARY                                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

success_count=0
for test in fs1 fs2 fs3 fs4 fp io; do
    flag_status="${flags[$test]}"
    if [ "$flag_status" != "NOT_FOUND" ]; then
        echo "✓ $test  →  $flag_status"
        ((success_count++))
    else
        echo "✗ $test  →  NO FLAG FOUND"
    fi
done

echo ""
echo "Summary: $success_count / 6 tests successful"
echo ""
