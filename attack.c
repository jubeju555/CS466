//gcc basic-return-2-libc.c -o ctf.exe -fno-stack-protector -no-pie -mpreferred-stack-boundary=2 -m32

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

void cmd_ls() {
	system("ls");
}

void cmd(char * envp[]) {
	char buffer[12];
	
	printf("$ ");
	
	gets(buffer);
	
	if(strcmp(buffer, "ls") == 0 || strcmp(buffer, "dir") == 0) {
		cmd_ls();
		printf("さよなら!\n");
	} else if(strcmp(buffer, "map") == 0) {
		FILE *fp;
		
		if ((fp = fopen("/proc/self/maps","r")) == NULL){
			printf("Error! opening file");

			// Program exits if the file pointer returns NULL.
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
		// printf("%p %p %p %p %p %p\n", exit, puts, printf, system, buffer, cmd);
		
		fclose(fp);
		
		system("ldd --version");
		system("ldd ctf.exe");
		system("strings -a -t x /lib/i386-linux-gnu/libc.so.6 | grep \"bin/sh\"");
		system("strings -a -t x /lib/i386-linux-gnu/libc.so.6 | grep system");
		system("readelf -s /lib/i386-linux-gnu/libc.so.6 | grep system");

	} 
	// else if(strcmp(buffer, "env") == 0) {
	// 	printf("%p", envp);
	// 	for (int i = 0; envp[i] != NULL; i++)
    //     	printf("\n%s %p", envp[i], &envp[i]);
	// } 
	else {
		printf("bash: command not found: %s\n",buffer);
		printf("さよなら!\n");
	}
	/*
	#include <gnu/libc-version.h>
	#include <stdio.h>
	#include <unistd.h>

	int main() {
		// method 1, use macro
		printf("%d.%d\n", __GLIBC__, __GLIBC_MINOR__);

		// method 2, use gnu_get_libc_version 
		puts(gnu_get_libc_version());

		// method 3, use confstr function
		char version[30] = {0};
		confstr(_CS_GNU_LIBC_VERSION, version, 30);
		puts(version);

		return 0;
	}
	*/
}

int main(int argc, char *argv[], char * envp[]){
	setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);

	cmd(envp);
	
	return 0;
}
