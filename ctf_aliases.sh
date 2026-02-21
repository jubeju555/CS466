#!/bin/bash
# CTF Challenge Aliases
# Source this file to enable quick navigation: source ~/CS466/ctf_aliases.sh

# Base CTF directory
export CTF_DIR="$HOME/CS466/ctf"

# Alias functions for each CTF challenge
utkctf() { cd "$CTF_DIR/01-utkctf"; }
png_stego() { cd "$CTF_DIR/02-png_stego"; }
minkaoctf2() { cd "$CTF_DIR/03-minkaoctf2"; }
utklogo() { cd "$CTF_DIR/04-utklogo"; }
stack_challenges() { cd "$CTF_DIR/05-stack_challenges"; }
bufferoverflow() { cd "$CTF_DIR/06-bufferoverflow"; }
bof-water18() { cd "$CTF_DIR/07-bof-water18"; }
stackoverflow-teleport() { cd "$CTF_DIR/08-stackoverflow-teleport"; }
bof-airport() { cd "$CTF_DIR/09-bof-airport"; }
shellcode() { cd "$CTF_DIR/10-shellcode"; }
shellcode2() { cd "$CTF_DIR/11-shellcode2"; }

# Shorter aliases for common ones
alias bof18='bof-water18'
alias bofwater18='bof-water18'
alias bof='bufferoverflow'
alias stack='stack_challenges'
alias teleport='stackoverflow-teleport'
alias shellcode='shellcode'
alias shellcode2='shellcode2'
alias ctf='cd $CTF_DIR'

echo "CTF aliases loaded! Use: utkctf, png_stego, minkaoctf2, utklogo, stack_challenges,"
echo "  bufferoverflow, bof-water18, stackoverflow-teleport, bof-airport, shellcode, shellcode2"
echo "Shortcuts: bof, stack, teleport, sc, sc2, ctf"
