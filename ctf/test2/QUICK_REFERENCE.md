# Quick Reference - Test2 Exploits

## Default Behavior (LOCAL MODE)
```bash
python3 fs1.py          # Runs locally against random-game
python3 fs2.py          # Runs locally against hidden_string
python3 fs3.py          # Runs locally against login
python3 fs4.py          # Runs locally against jump
./run_all_tests.sh      # Runs all 6 exploits locally
```

## Remote Testing (Explicit)
```bash
# Individual script
python3 fs1.py --mode remote --host ctf.example.com --port 9000

# All scripts with unified port
./runall.sh --mode remote
# Prompts: "shared port [32100]: 9000"
# Then runs all 4 with port 9000
```

## Exam Mode
```bash
# Run all, stop on first flag, 10s timeout
./runall.sh --stop-on-flag --timeout 10
```

## Port Summary
- **Local Mode**: Ports ignored (uses binaries locally)
- **Remote Mode**: Each script accepts --host and --port
- **runall.sh**: Prompts for single shared port when remote

## Files in test2
| File | Purpose |
|------|---------|
| fs1.py | formatstring1 leak+repeat exploit |
| fs2.py | formatstring2 string leak exploit |
| fs3.py | formatstring3 global write exploit (adaptive) |
| fs4.py | formatstring4 return-overwrite exploit (adaptive) |
| fp.py | framepointer pivot exploit |
| io.py | integer-overflow exploit |
| runall.sh | Run all 4 format-string exploits |
| run_all_tests.sh | Run all 6 exploits with detailed output |
| random-game | formatstring1 binary |
| hidden_string | formatstring2 binary |
| login | formatstring3 binary |
| jump | formatstring4 binary |
| challenge | framepointer binary |
| challenge-io | integer-overflow binary |

## Status
✅ All scripts default to local mode
✅ All ports configurable for remote testing
✅ runall.sh provides unified port management
✅ No hardcoded ports in scripts (only fallback defaults)
✅ All 6 challenges working locally
