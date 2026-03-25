#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int utk_password = 0x12341234;

int myutk_login(char *kim_password) {
	printf(kim_password);
	printf("%x %p\n", utk_password, &utk_password);
	if (utk_password == 0xD0C0FFEE) {
        	system("cat flag.txt");
	}
	else {
		printf("Wrong Dr. Kim's password. You are't allowed to log in to his MyUTK\n");
	}
}

int main()
{
	setbuf(stderr, NULL);
	setbuf(stdin, NULL);
	setbuf(stdout, NULL);

	char kim_password[128];
	printf("%s\n", "What's Dr. Kim's password for MyUTK?");
	fgets(kim_password, sizeof(kim_password), stdin);

	myutk_login(kim_password);
}
