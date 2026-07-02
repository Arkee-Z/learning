#define SIMPLE_IO_IMPLEMENTATION
#define IO_BUFFER
#include "../arrays/lib/simple_io.h"

int main(int argc, char *argv[]) {

    if (argc != 3) {

        fprintf(stderr, "Usage: %s source destination\n", argv[0]);
        return 1;
    }

    if (copy_file(argv[1], argv[2]) != 0) {

        perror("simple_cp");
        return 1;
    }

    return 0;
}