#define COPY_INPUT_TO_OUTPUT_IMPLEMENTATION
#include "copy_input_to_output.h"

int main(int argc, char *argv[]) {

    if (argc != 3) {

        fprintf(stderr, "Usage: %s source destination\n", argv[0]);
        return 1;
    }

    if (copy_file(argv[1], argv[2], 0) != 0) {

        perror("simple_cp");
        return 1;
    }
    return 0;
}