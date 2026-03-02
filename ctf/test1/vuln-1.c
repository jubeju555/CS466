#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void shellcode(){
    system("cat flag.txt");
}

void hackthis(){
      int key = 0xabcd1234;
      char buf[24];
      char buf2[12];

      printf("please hack me: \n");
      gets(buf);
      if(key == 0xbeefcafe){
            system("ls");
      }
      else{
            printf("It doesn't work.\n");
      }
}

int main(int argc, char* argv[]){
      char buf[32];
      
      setbuf(stdout, NULL);
      setbuf(stdin, NULL);
      setbuf(stderr, NULL);
      
      hackthis();
      return 0;
}
