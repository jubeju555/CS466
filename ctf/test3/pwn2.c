#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>

unsigned char shellcode[] = 
"\x31\xc0"             // xor eax, eax (Zero out EAX)
"\x50"                 // push eax     (Push null terminator for string)
"\x68\x2f\x2f\x73\x68" // push //sh    (Push "/sh" string)
"\x68\x2f\x62\x69\x6e" // push /bin    (Push "/bin" string)
"\x89\xe3"             // mov ebx, esp (Set EBX to point to "/bin//sh")
"\x50"                 // push eax     (Push NULL for argv[1])
"\x53"                 // push ebx     (Push pointer to "/bin//sh" for argv[0])
"\x89\xe1"             // mov ecx, esp (Set ECX to argv)
"\xb0\x0b"             // mov al, 0xb  (Syscall 11: execve)
"\xcd\x80";            // int 0x80     (Interrupt to trigger syscall)

unsigned char str[] = {0x2f, 0x62, 0x69, 0x6e, 0x2f, 0x73, 0x68, 0x00};

void cmd_ls() {
	system("ls");
}
void shell_code() {
	size_t len = sizeof(shellcode) - 1;
	for (size_t i = 0; i < len; i++) {
        	printf("\\x%02x", shellcode[i]);
    	}
	printf("\n");
}

void maps() {
	FILE *fp;
	if ((fp = fopen("/proc/self/maps","r")) == NULL){
		printf("Error! opening file");

		exit(1);
	}
	int c;
	while(1) {
		c = fgetc(fp);
		if( feof(fp) ) {
			break;
		}
		printf("%c", c);
	}	
	
	fclose(fp);

}
void map() {
	system("readelf -s /lib/i386-linux-gnu/libc.so.6 | grep sys");
	maps();
}

void cmd() {
	char buffer1[8];
	char buffer2[24];
	char buffer3[8];
	int tmp;

	printf("You have three commands: ls, map, and shell\n");
	printf("$ ");
	gets(buffer2);
	
	if(strcmp(buffer2, "ls") == 0) {
		cmd_ls();
	} 
	else if (strcmp(buffer2, "map") == 0) {
		map(buffer2);
	}
	else if(strcmp(buffer2, "shell") == 0) {
		tmp = str;
		printf("%08x, %08x, %08x, %08x\n", buffer1, buffer2, buffer3, tmp);
		shell_code();
	}
	else {
		printf("bash: command not found: %s\n", buffer3);
	}
	
	printf("ByeByeBye!\n");
}

int main() {
	setbuf(stdout, NULL);
    	setbuf(stdin, NULL);
    	setbuf(stderr, NULL);

	cmd();
	
	return 0;
}
