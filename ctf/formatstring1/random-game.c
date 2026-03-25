#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

int main(int argc, char** argv) {

    int size = 16;
    int passcode;
    char buf[size];

    srand(time(NULL));
    passcode = rand();
    
    setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);

    printf("------------------------------------------\n");
    printf(">> What's the passcode to enter here?\n");
    fflush(stdout);
    fgets(buf, size, stdin);
    printf(buf);

    int yourcode = 0x12341234;
    printf(">> Again! What's the passcode to enter here?\n");
    fflush(stdout);
    scanf("%x", &yourcode);
    
    if(passcode == yourcode){
        puts(">> Oh. You got the passcode to enter here. Flag is ");
        system("cat flag.answer");
    } else {
        puts(">> Wrong! You are NOT allowed to enter here!\n");
    }

    return 0;
}
