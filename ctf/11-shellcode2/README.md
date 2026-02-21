# Shellcode2 Challenge

Advanced buffer overflow with JMP ESP shellcode injection technique.

## Quick Start

```bash
python3 exploit.py
```

## Challenge Details

- **Type:** Buffer Overflow + JMP ESP Shellcode Injection
- **Architecture:** 32-bit x86
- **Protections:** Executable stack
- **Server:** moa6.eecs.utk.edu:6055
- **Binary:** `shellcode2`

## Solution Summary

This challenge includes a **misleading hint** that teaches you to verify everything!

1. **Hint address (`0x80499ac`):** WRONG - Just prints the hint message
2. **Real target (`0x080499a7`):** CORRECT - JMP ESP gadget in the `jump` function
3. **Offset:** 12 bytes (8 byte buffer + 4 byte saved EBP)
4. **Technique:** JMP ESP - return to a `jmp esp` instruction, which then jumps to shellcode on the stack
5. **Payload:** `[12 bytes padding] + [0x080499a7] + [shellcode]`

### Why 0x080499a7 and not 0x80499ac?

The program hints at `0x80499ac`, but that's the start of `print_jump_addr()` function (which just prints the hint). The **real** target is at `0x080499a7` - the address of a `jmp esp` instruction inside the `jump()` function.

You find this by:
1. Listing all functions with `info functions`
2. Noticing the `jump` function at `0x0804999a`
3. Disassembling it: `disassemble jump`
4. Finding `jmp esp` at offset +13 = `0x080499a7`

## Files

- `shellcode2` - Challenge binary
- `exploit.py` - Working exploit script  
- `.gdb_history` - GDB commands used during analysis
- `walkthrough.md` - Detailed step-by-step solution

## Key Learning Points

- **Don't trust hints blindly** - Always verify!
- **Explore adjacent functions** - The answer was near the hint function
- **JMP ESP technique** - Classic shellcode delivery method
- **Gadget hunting** - Finding useful instruction sequences in binaries
- **Address precision** - One instruction can make all the difference

## Flag

```
cosc466-flag-{Pxky6X6D5nXRwpnm}
```

For a complete walkthrough explaining why we disassembled `jump` and how we found the real address, see [walkthrough.md](walkthrough.md).
