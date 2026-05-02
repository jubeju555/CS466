// ret2libc_practice.c
// Compile:
// gcc ret2libc_practice.c -o practice -m32 -fno-stack-protector -no-pie -mpreferred-stack-boundary=2 -g

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void banner() {
    puts("=== Secure Login Portal ===");
}

void hint() {
    FILE *fp = fopen("/proc/self/maps", "r");
    if (!fp) {
        perror("fopen");
        exit(1);
    }

    int c;
    while ((c = fgetc(fp)) != EOF) {
        putchar(c);
    }

    fclose(fp);

    puts("\n--- libc hints ---");
    system("ldd --version");
    system("strings -a -t x /usr/lib/i386-linux-gnu/libc.so.6 | grep '/bin/sh'");
    system("readelf -s /usr/lib/i386-linux-gnu/libc.so.6 | grep ' system@@'");
    system("readelf -s /usr/lib/i386-linux-gnu/libc.so.6 | grep ' exit@@'");
}

void login() {
    char username[20];
    int authenticated = 0;

    printf("username: ");
    gets(username);

    if (strcmp(username, "hint") == 0) {
        hint();
        return;
    }

    if (authenticated == 0x1337) {
        puts("Welcome admin.");
    } else {
        printf("Access denied for %s\n", username);
    }
}

int main() {
    setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);

    banner();
    login();

    return 0;
}
