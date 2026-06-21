#include <stdio.h>
#include <stdlib.h>

typedef struct {
    char *data;
    size_t length;
    size_t capacity;
} IOBuffer;

void count_line_in_input() {

    int c, nl, nc, tc, bc, blc;

    nl = 0;
    while ((c = getchar()) != EOF) {

        if (c == '\t') 
            ++tc;
        else if (c == '\n') 
            ++nl;
        else if (c == ' ') 
            ++blc;
        else if (c == '\b')
            ++bc;
        ++nc;
        printf("nc = %d", nc);
        printf("nl = %d", nl);
    }
}

// int buffer_initial() {

// }

// int buffer_expand(IOBuffer *buf) {


// }

IOBuffer copy_input_to_buffer(void) {

    int c;
    size_t size = 0;
    size_t capacity = 16;

    char *buffer = malloc(capacity);
    if (buffer == NULL) {

        fprintf(stderr, "ERROR: Buffer memory allocation failed! \n");
        return (IOBuffer){NULL, 0, 16};
    }

    printf("Input something, end with '#': \n");
    while ((c = getchar()) != EOF && c != '#') {

        if(size >= capacity) {

            capacity *= 2;
            char *new_buffer = realloc(buffer, capacity);
            if (new_buffer == NULL) {
                free(buffer);
                fprintf(stderr, "ERROR: Buffer memory reallocation failed! \n");
                return (IOBuffer){NULL, 0, 16};
            } 
            buffer = new_buffer;
        }
        buffer[size++] = (char)c;
    }
    if (size == 0) {
        free(buffer);
        return (IOBuffer){NULL, 0, 16};;
    }
    return (IOBuffer){buffer, size, capacity};
}

void print_buffer(const char *buffer, size_t length) {
    
    fwrite(buffer, 1, length, stdout);
    printf("\n");
}

int copy_input_to_output() {

    IOBuffer buf = copy_input_to_buffer();

    if (buf.data == NULL) {
        fprintf(stderr, "ERROR: Buffer memory is null! \n");
        return EXIT_FAILURE;
    }
    print_buffer(buf.data, buf.length);
    free(buf.data);

    return EXIT_SUCCESS;
}

int main(void) {

/* copy input to output; 1st version */

    // int c;

    // c = getchar();
    // while (c != EOF) {
    //     putchar(c);
    //     c = getchar();
    // }

/* copy input to output; 2st version */

    // int c;

    // // printf("%d", EOF);
    // while ((c = getchar()) != EOF) {

    //     putchar(c);
    // }

    copy_input_to_output();

}