#include <stdio.h>
#include <string.h>

void win() {
    printf("You won this game! Congrats!\n");
    system("/bin/sh");
}
void vul_func() {
    char buf[32];
    printf("buf @ 0x%08x\n", buf);
    printf("win() @ 0x%08x\n", win);
    read(0, buf, 36);
    printf(buf);
}

void run() {
    volatile int x = 0;
    vul_func();
}	

int main(int argc, char *argv[]) {
    setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);
    run();
    return 0;
}
