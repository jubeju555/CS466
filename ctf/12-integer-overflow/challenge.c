#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <string.h>

static int read_u32(uint32_t *out)
{
    char tmp[32];
    size_t i = 0;
    char c = '\0';

    while (i + 1 < sizeof(tmp))
    {
        ssize_t n = read(0, &c, 1);
        if (n <= 0)
        {
            return 0;
        }
        if (c == '\n')
        {
            break;
        }
        tmp[i++] = c;
    }

    tmp[i] = '\0';
    *out = (uint32_t)strtoul(tmp, NULL, 10);
    return 1;
}

void jump(void)
{
    puts("cosc466-flag-{1nt3g3r_0v3rfl0w}");
    _exit(0);
}

void vuln(void)
{
    char buf[64];
    uint32_t count = 0;
    uint16_t checked_bytes = 0;

    puts("How many 8-byte chunks?");
    if (!read_u32(&count))
    {
        return;
    }

    checked_bytes = (uint16_t)(count * 8u);

    if (checked_bytes > sizeof(buf))
    {
        puts("Too large!");
        return;
    }

    puts("Send payload:");
    read(0, buf, (size_t)count * 8u);
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    printf("jump() @ %p\n", (void *)jump);
    vuln();
    puts("Goodbye!");
    return 0;
}
