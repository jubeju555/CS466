#!/bin/bash
# CTF Challenge Aliases
# Source this file to enable quick navigation: source ~/CS466/ctf_aliases.sh
# Or add to ~/.bashrc: source ~/CS466/ctf_aliases.sh

# Base CTF directory
export CTF_DIR="$HOME/CS466/ctf"

# Override cd command to handle CTF challenge names
cd() {
    case "$1" in
        utkctf)
            builtin cd "$CTF_DIR/01-utkctf"
            ;;
        png_stego)
            builtin cd "$CTF_DIR/02-png_stego"
            ;;
        minkaoctf2)
            builtin cd "$CTF_DIR/03-minkaoctf2"
            ;;
        utklogo)
            builtin cd "$CTF_DIR/04-utklogo"
            ;;
        stack_challenges|stack)
            builtin cd "$CTF_DIR/05-stack_challenges"
            ;;
        bufferoverflow|bof)
            builtin cd "$CTF_DIR/06-bufferoverflow"
            ;;
        bof-water18|bof18|bofwater18)
            builtin cd "$CTF_DIR/07-bof-water18"
            ;;
        stackoverflow-teleport|teleport)
            builtin cd "$CTF_DIR/08-stackoverflow-teleport"
            ;;
        bof-airport)
            builtin cd "$CTF_DIR/09-bof-airport"
            ;;
        shellcode|sc)
            builtin cd "$CTF_DIR/10-shellcode"
            ;;
        shellcode2|sc2)
            builtin cd "$CTF_DIR/11-shellcode2"
            ;;
        ctf)
            builtin cd "$CTF_DIR"
            ;;
        *)
            builtin cd "$@"
            ;;
    esac
}

echo "CTF aliases loaded! Now you can use: cd bof, cd shellcode, cd stack, etc."
echo "Available: utkctf, png_stego, minkaoctf2, utklogo, stack, bof, bof18,"
echo "  teleport, bof-airport, shellcode (sc), shellcode2 (sc2), ctf"
