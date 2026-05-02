// gcc challenge.c -o challenge -fno-stack-protector -no-pie -m32

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

char staging[128];

__attribute__((naked)) void popret(void)
{
    __asm__("pop %ebx; ret;");
}

void service(void)
{
    char buffer[12];

    puts("ret2libc practice shell");
    puts("type map for hints, or anything else to continue");
    printf("$ ");

    gets(buffer);

    if (strcmp(buffer, "map") == 0)
    {
        FILE *fp = fopen("/proc/self/maps", "r");
        if (fp == NULL)
        {
            puts("Error opening /proc/self/maps");
            exit(1);
        }

        int c;
        while ((c = fgetc(fp)) != EOF)
        {
            putchar(c);
        }

        fclose(fp);
        puts("\nHint: the real exam will not give you a helper leak like this.");
    }
    else if (strcmp(buffer, "help") == 0)
    {
        puts("Use the overflow to leak libc, then call system() yourself.");
    }
    else
    {
        printf("unknown: %s\n", buffer);
    }
}

int main(void)
{
    setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);

    service();
    return 0;
}
