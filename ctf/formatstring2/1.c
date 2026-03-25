#include <stdio.h>
#include <stdlib.h>

char* read_flag(void) {
	FILE* f = fopen("flag.txt", "r");
	char* flag = calloc(64, sizeof(char));
	fscanf(f, "%63s", flag);
	fclose(f);
	return flag;
}

int main() {
	char* flag = read_flag();

	printf("What's your name? ");
    fflush(stdout);
	
	char name[24];
	scanf("%24s", name);
	
	printf("Hello, ");
	printf(name);
	printf(", how are you?\n");
	
	fflush(stdout);

	return 0;
}
