#include <stdio.h>
#include <unistd.h>                                                                                                                                                 
#include <stdlib.h>

void jump() {
	printf("fff");
	system("/bin/bash");
}

int main(){
	char buffer[32];
	
	setbuf(stdout, NULL);
    	setbuf(stdin, NULL);
    	setbuf(stderr, NULL);
	printf("%p\n", __builtin_return_address(0));
	printf("%x %x %x %x\n", buffer[48], buffer[49], buffer[50], buffer[51]);
	printf("Let me jump to the function %x, %x. Give me the code for teleport.\n", jump, &buffer);
	fgets(buffer, sizeof(buffer), stdin);
	printf(buffer);
	printf("\nWrong!!!!!\n%s\n", buffer);
	
	printf("%x %x %x %x\n", buffer[48], buffer[49], buffer[50], buffer[51]);
	return 0;
}
