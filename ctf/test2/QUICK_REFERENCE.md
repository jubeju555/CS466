# Quick Reference - Test2 Exploits

## Default Behavior (LOCAL MODE)
```bash
python3 fs1.py          # Runs locally against random-game
python3 fs2.py          # Runs locally against hidden_string
python3 fs3.py          # Runs locally against login
python3 fs4.py          # Runs locally against jump
./run_all_tests.sh      # Runs every exploit against every bundled binary
./runall.sh             # Same local matrix, with flag detection and optional stop-on-flag
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
# Run the local matrix, stop on first flag, 10s timeout
./runall.sh --stop-on-flag --timeout 10
```

## Port Summary
- **Local Mode**: Ports ignored (uses binaries locally)
- **Remote Mode**: Each script accepts --host and --port
- **runall.sh**: Local mode runs the full script-vs-binary matrix; remote mode prompts for a single shared port

## Files in test2
| File | Purpose |
|------|---------|
| fs1.py | formatstring1 leak+repeat exploit |
| fs2.py | formatstring2 string leak exploit |
| fs3.py | formatstring3 global write exploit (adaptive) |
| fs4.py | formatstring4 return-overwrite exploit (adaptive) |
| fp.py | framepointer pivot exploit |
| io.py | integer-overflow exploit |
| runall.sh | Run the local script-vs-binary matrix or the remote format-string set |
| run_all_tests.sh | Local wrapper for the exhaustive matrix runner |
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
✅ Local matrix covers every script against every bundled binary
