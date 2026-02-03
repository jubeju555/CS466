# Steganography Challenge - Command Reference Guide

## Overview
This guide explains all the commands used to solve the byte-comparison steganography challenge where a flag was hidden by modifying specific bytes in an image.

---

## 1. Basic Navigation & File Listing

### Change Directory and Show Location
```bash
cd /home/judah/CS466 && pwd
```
- `cd` = **c**hange **d**irectory - navigate to a folder
- `&&` = run next command only if first command succeeds
- `pwd` = **p**rint **w**orking **d**irectory - shows your current location

**Example Output:**
```
/home/judah/CS466
```

### List Files with Details
```bash
ls -lh
```
- `ls` = **l**i**s**t files and directories
- `-l` = long format (shows permissions, owner, size, date)
- `-h` = human-readable file sizes (KB, MB instead of bytes)

**Example Output:**
```
-rw-r--r-- 1 judah judah 470K Jan 28 18:24 TCE_Min-Kao.jpg
-rw-r--r-- 1 judah judah 470K Jan 28 18:24 TCE_Min-Kao2.jpg
```

### List Only Specific File Types
```bash
ls -lh *.jpg
```
- `*.jpg` = wildcard pattern (matches all files ending in .jpg)

---

## 2. File Information Commands

### Identify File Type
```bash
file filename.jpg
```
- `file` = examines a file and tells you what type it is
- Works by reading the file's internal structure (magic bytes)

**Example Output:**
```
utk-logo2_2.jpg: JPEG image data, Exif standard, progressive, 
                 precision 8, 1611x1275, components 4
```

### Generate File Checksum
```bash
md5sum filename.jpg
```
- `md5sum` = creates a unique "fingerprint" (hash) of the file
- If even one byte changes, the hash is completely different
- Useful for verifying file integrity or checking if files are identical

**Example Output:**
```
e42817dd4e129a26d5f5c1546363baed  utk-logo2_2.jpg
```

---

## 3. Finding Files

### Basic File Search
```bash
find . -name "*.jpg"
```
- `find` = search for files in directory tree
- `.` = start searching from current directory
- `-name "*.jpg"` = find files matching this pattern
- `*` = wildcard (matches anything)

### Search for Multiple File Types
```bash
find . -name "*.jpg" -o -name "*.jpeg" -o -name "*.png"
```
- `-o` = **OR** operator (match any of these patterns)

**Example Output:**
```
./TCE_Min-Kao.jpg
./TCE_Min-Kao2.jpg
./ctf/utklogo/utk-logo2_2.jpg
./ctf/minkaoctf/image1.jpg
```

### Search and Sort Results
```bash
find . -name "*.jpg" | sort
```
- `|` = **pipe** - sends output of first command as input to second
- `sort` = alphabetically sort the results

### Limit Results
```bash
find . -name "*utk*" | head -20
```
- `head -20` = show only first 20 lines of output
- `tail -20` = show only last 20 lines

---

## 4. File Comparison Commands

### Compare Two Files (Basic)
```bash
cmp file1.jpg file2.jpg
```
- `cmp` = **c**o**mp**are two files byte-by-byte
- Returns nothing if identical, shows first difference if different

**Example Output:**
```
file1.jpg file2.jpg differ: byte 173239, line 1
```

### Compare and Show All Differences
```bash
cmp -l file1.jpg file2.jpg
```
- `-l` = **l**ist all differences with byte positions and values

**Example Output:**
```
173239  147  143
173255  212  157
173271  010  163
```
Format: `byte_position  octal_value_file1  octal_value_file2`

### Compare Hex Dumps
```bash
diff <(xxd file1) <(xxd file2)
```
- `xxd` = creates hex dump of file
- `<(command)` = process substitution (treats command output as file)
- `diff` = shows line-by-line differences

---

## 5. Examining File Contents

### View File in Hexadecimal
```bash
xxd file.jpg | head -20
```
- `xxd` = make a hex dump (shows file bytes in hexadecimal)
- Each line shows: offset, hex bytes, ASCII representation

**Example Output:**
```
00000000: ffd8 ffe0 0010 4a46 4946 0001 0101 0048  ......JFIF.....H
00000010: 0048 0000 ffe1 0016 4578 6966 0000 4d4d  .H......Exif..MM
```

### View with hexdump (Alternative)
```bash
hexdump -C file.jpg | less
```
- `-C` = canonical hex+ASCII display
- `less` = paginate output (scroll with arrows, quit with 'q')

### Extract Readable Strings
```bash
strings file.jpg
```
- `strings` = extract all printable ASCII strings from a file
- Useful for finding hidden text, URLs, metadata

**Example Output:**
```
JFIF
Exif
Adobe
cosc466-flag-{secret}
```

### Count Lines, Words, or Bytes
```bash
wc -l file.txt      # count lines
wc -w file.txt      # count words
wc -c file.jpg      # count bytes
```

---

## 6. Python Binary File Operations

### Read File in Binary Mode
```python
with open('file.jpg', 'rb') as f:
    data = f.read()
```
- `'rb'` = **r**ead **b**inary mode
- Returns data as bytes (numbers 0-255), not text
- `data[0]` gives you the first byte as an integer

### Compare Two Files Byte-by-Byte
```python
with open('file1.jpg', 'rb') as f1, open('file2.jpg', 'rb') as f2:
    data1 = f1.read()
    data2 = f2.read()
    
for i in range(len(data1)):
    if data1[i] != data2[i]:
        print(f"Difference at byte {i}: {data1[i]} vs {data2[i]}")
```

### Convert Byte to Character
```python
byte_value = 99
char = chr(byte_value)  # chr(99) = 'c'
```

### Check if Byte is Printable ASCII
```python
if 32 <= byte_value <= 126:
    print(f"Printable: {chr(byte_value)}")
else:
    print(f"Non-printable: {byte_value}")
```
- ASCII printable range: 32 (space) to 126 (~)

---

## 7. Advanced Command Combinations

### Redirect Output to File
```bash
find . -name "*.jpg" > list.txt
```
- `>` = redirect output to file (overwrites)
- `>>` = append to file

### Suppress Error Messages
```bash
find . -name "*.jpg" 2>/dev/null
```
- `2>` = redirect error messages (stderr)
- `/dev/null` = discard the output (trash can)

### Run Multiple Commands
```bash
cd /home/judah && ls -lh && pwd
```
- `&&` = run next command only if previous succeeded
- `||` = run next command only if previous failed
- `;` = run next command regardless

---

## 8. How the Steganography Challenge Was Solved

### Step 1: Find the Two Images
```bash
find . -name "*Min-Kao*"
```
Found: `TCE_Min-Kao.jpg` and `TCE_Min-Kao2.jpg`

### Step 2: Verify They're the Same Size
```bash
ls -lh TCE_Min-Kao.jpg TCE_Min-Kao2.jpg
```
Both were 470K - same size but different content!

### Step 3: Compare Byte-by-Byte
```bash
python3 compare_images.py TCE_Min-Kao.jpg TCE_Min-Kao2.jpg
```

The script found 23 different bytes out of 480,370 total bytes.

### Step 4: Extract the Flag
The modified bytes in the second image spelled out:
```
cosc466-flag-{bpK6QX#7}
```

**How it worked:**
- Byte 173239: value 99 = 'c'
- Byte 173255: value 111 = 'o'  
- Byte 173271: value 115 = 's'
- Byte 173287: value 99 = 'c'
- ... and so on for all 23 bytes

---

## 9. Useful CTF/Forensics Tools

### Image Analysis
```bash
exiftool image.jpg          # Extract all metadata
identify -verbose image.jpg # ImageMagick info
binwalk image.jpg           # Find embedded files
steghide extract -sf image.jpg  # Extract steganographic data
```

### Binary Analysis
```bash
od -A x -t x1z -v file      # Octal dump
strings -n 8 file           # Strings 8+ chars long
file -b file                # Brief file type
```

### Hash Comparison
```bash
md5sum file1 file2          # Compare checksums
sha256sum file              # More secure hash
```

---

## 10. Quick Reference Cheat Sheet

| Command | Purpose | Example |
|---------|---------|---------|
| `cd` | Change directory | `cd /home/user` |
| `pwd` | Show current directory | `pwd` |
| `ls -lh` | List files (detailed) | `ls -lh *.jpg` |
| `find` | Search for files | `find . -name "*.txt"` |
| `file` | Identify file type | `file image.jpg` |
| `xxd` | Hex dump | `xxd file.bin \| head` |
| `strings` | Extract text | `strings binary` |
| `cmp` | Compare files | `cmp -l file1 file2` |
| `diff` | Show differences | `diff file1 file2` |
| `md5sum` | File checksum | `md5sum file` |
| `grep` | Search in text | `grep "flag" file.txt` |
| `\|` | Pipe output | `ls \| sort` |
| `>` | Redirect to file | `echo "hi" > file.txt` |
| `&&` | Chain commands | `cd dir && ls` |

---

## Additional Resources

### Man Pages (Manual)
```bash
man command_name      # Read full documentation
man ls                # Example: ls manual
```

### Command Help
```bash
command_name --help   # Quick help
ls --help
```

### Search for Command
```bash
apropos keyword       # Find commands related to keyword
apropos "search"
```

---

**Pro Tip:** When solving CTF challenges, always:
1. Check file types with `file`
2. Look for strings with `strings`
3. Compare similar files with `cmp -l` or byte-by-byte comparison
4. Check metadata with `exiftool`
5. Think about what the hint is telling you!
