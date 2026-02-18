#include <stdio.h>

int main() {
    int desk = 0x18181818;
    char water[30];

    setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);

    puts("Opps! I just pour water on the desk:");
    gets(water);

    if (desk != 0x18181818) {
        puts("Please use the below flag to clean up the water on the desk!");
        system("cat flag.answer");
    }
}

