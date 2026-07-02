#define SIMPLE_IO_IMPLEMENTATION
#define IO_BUFFER
#include "../arrays/lib/simple_io.h"

int main(int argc, char *argv[]) {

    if (argc == 1) {

        return copy_stream(stdin, stdout);
    }

    int ret = 0;
    for (int i = 1; i < argc; i++) {

        FILE *fp = fopen(argv[i], "rb");
        if (!fp) {

            fprintf(stderr, "simple_cat: %s: No such file or directory\n", argv[i]);
            ret = 1;
            continue;
        }

        if (copy_stream(fp, stdout) != 0) {

            fprintf(stderr, "simple_cat: %s: Read error\n", argv[i]);
            ret = 1;
        }

        fclose(fp);
    }

    return ret;
}