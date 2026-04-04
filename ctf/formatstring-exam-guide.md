# Format String Exam Guide

Use this as the fast decision sheet during the exam. The goal is to recognize the code pattern first, then pick the right script immediately.

## The 4 Challenge Types

| Folder | What the code is doing | What you exploit | Script to use |
|--------|-------------------------|------------------|---------------|
| [formatstring1](formatstring1/formatstring1-walkthrough.md) | `printf(buf)` leaks a stack value, then the program asks you to type the passcode back | Stack leak only | [exploit_remote.py](formatstring1/exploit_remote.py) |
| [formatstring2](formatstring2/formatstring2-walkthrough.md) | `printf(name)` prints a pointer as a string | String leak with `%7$s` | [exploit_local.py](formatstring2/exploit_local.py) or [exploit_remote.py](formatstring2/exploit_remote.py) |
| [formatstring3](formatstring3/formatstring3-walkthrough.md) | `printf(kim_password)` lets you write to a global integer check | Global variable write with `%hn` | [exploit_fs3.py](formatstring3/exploit_fs3.py) |
| [formatstring4](formatstring4/formatstring4-walkthrough.md) | `printf(buffer)` lets you overwrite the saved return address | Return-address overwrite with `%hn` | [exploit_easy.py](formatstring4/exploit_easy.py) or [exploit.py](formatstring4/exploit.py) |

## How to tell them apart quickly

### 1. If the program asks for a value twice

Look for a flow like:

- first prompt: you type something that gets printed with `printf(buf)`
- second prompt: the program asks you to type a number back

That is [formatstring1](formatstring1/formatstring1-walkthrough.md).

What to do:

1. Leak the stack value with `%6$x`.
2. Type the leaked hex value back at the second prompt.
3. Use [formatstring1/exploit_remote.py](formatstring1/exploit_remote.py) if you want the helper script.

### 2. If the code reads a flag into memory and then does `printf(name)`

Look for this pattern:

- a function loads `flag.txt` into a pointer
- the pointer sits in a local variable
- user input goes into a small buffer
- the buffer is used directly as the format string

That is [formatstring2](formatstring2/formatstring2-walkthrough.md).

What to do:

1. Send `%7$s`.
2. Read the flag directly from the printed output.
3. Use [formatstring2/exploit_local.py](formatstring2/exploit_local.py) for local testing or [formatstring2/exploit_remote.py](formatstring2/exploit_remote.py) for the server.

### 3. If the code compares a global integer to a magic constant

Look for these clues:

- a global variable like `utk_password`
- a comparison against a hardcoded value
- the program prints the variable address or current value

That is [formatstring3](formatstring3/formatstring3-walkthrough.md).

What to do:

1. Use the leak to confirm the stack offset.
2. Build a two-halfword `%hn` payload.
3. Write the target 32-bit value into the global variable.
4. Use [formatstring3/exploit_fs3.py](formatstring3/exploit_fs3.py).

### 4. If the code leaks a function address and a stack buffer address

Look for these clues:

- the program prints a target function pointer like `jump`
- it prints the stack buffer address too
- you need to redirect control flow, not just print data

That is [formatstring4](formatstring4/formatstring4-walkthrough.md).

What to do:

1. Compute the saved return address from the buffer leak.
2. Split the target address into high and low halfwords.
3. Use two `%hn` writes to overwrite the return address.
4. Use [formatstring4/exploit_easy.py](formatstring4/exploit_easy.py) if you want the hand-calculation version, or [formatstring4/exploit.py](formatstring4/exploit.py) if you want the scripted exploit.

## Exam Decision Tree

Ask these questions in order:

1. Is the goal just to reveal a hidden value? If yes, think leak.
2. Do I need to type the leaked value back? If yes, think [formatstring1](formatstring1/formatstring1-walkthrough.md).
3. Do I see `printf(name)` with a hidden pointer or flag string? If yes, think [formatstring2](formatstring2/formatstring2-walkthrough.md).
4. Do I need to change a global variable to pass a check? If yes, think [formatstring3](formatstring3/formatstring3-walkthrough.md).
5. Do I need to overwrite the return address or jump to another function? If yes, think [formatstring4](formatstring4/formatstring4-walkthrough.md).

## What each script is for

- [formatstring1/exploit_remote.py](formatstring1/exploit_remote.py): sends `%6$x`, parses the leak, and feeds it back.
- [formatstring2/exploit_local.py](formatstring2/exploit_local.py): local version for `%7$s`.
- [formatstring2/exploit_remote.py](formatstring2/exploit_remote.py): remote version for `%7$s`.
- [formatstring3/exploit_fs3.py](formatstring3/exploit_fs3.py): finds the stack offset, then writes the full 32-bit value with two `%hn` writes.
- [formatstring4/exploit_easy.py](formatstring4/exploit_easy.py): easiest to study because it prints the leak math before sending the payload.
- [formatstring4/exploit.py](formatstring4/exploit.py): fuller exploit wrapper with local and remote support.

## Short memory version

If you freeze during the exam, remember this line:

- leak and type back = [formatstring1](formatstring1/formatstring1-walkthrough.md)
- print hidden string = [formatstring2](formatstring2/formatstring2-walkthrough.md)
- write global variable = [formatstring3](formatstring3/formatstring3-walkthrough.md)
- overwrite return address = [formatstring4](formatstring4/formatstring4-walkthrough.md)

## One-line summaries

- [formatstring1](formatstring1/formatstring1-walkthrough.md): stack leak, then repeat the leaked passcode.
- [formatstring2](formatstring2/formatstring2-walkthrough.md): use `%7$s` to print the hidden flag string.
- [formatstring3](formatstring3/formatstring3-walkthrough.md): use `%hn` to write the needed value into a global integer.
- [formatstring4](formatstring4/formatstring4-walkthrough.md): use `%hn` to overwrite the saved return address and jump to `jump()`.