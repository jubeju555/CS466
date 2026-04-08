#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdint.h>

void jump(void)
{
    puts("cosc466-flag-{fp_h4rd3r}");
    _exit(0);
}

void vuln(void)
{
    char buf[8];
    printf("buf @ 0x%08x\n", buf);
    read(0, buf, 12);
}

void caller(void)
{
    volatile int x = 0;
    vuln();
}

int main(void)
{

    caller();

    puts("Goodbye!");
    return 0;
}
