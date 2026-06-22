// copy_input_to_output.h 

#ifndef COPY_INPUT_TO_OUTPUT_H
#define COPY_INPUT_TO_OUTPUT_H

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

typedef struct {

    size_t lines;
    size_t words;
    size_t bytes; 
} CountResult;

CountResult stream_cnt = {0};

CountResult buf_count(unsigned char *buf, size_t n);
int copy_stream(FILE *in, FILE *out, size_t bufsize);
int copy_file(const char *src, const char *dst, size_t bufsize);

// ============ STB implementation ============
#ifdef COPY_INPUT_TO_OUTPUT_IMPLEMENTATION

CountResult buf_count(unsigned char *buf, size_t n) {

    bool is_in_word = false;
    CountResult cnt = {0};
    if (!buf) return (CountResult){0, 0, 0};
    for (size_t i = 0; i < n; i++) {

        if (buf[i] == '\n') cnt.lines++;
        if (buf[i] == ' ' || buf[i] == '\n' || buf[i] == '\t') {

            is_in_word = false;
        } else if (is_in_word == false) {

            is_in_word = true;
            cnt.words++;
        }
    }
    cnt.bytes = n;
    return cnt;
}

int copy_stream(FILE *in, FILE *out, size_t bufsize) {

    if (bufsize == 0) bufsize = 65536;
    unsigned char *buf = malloc(bufsize);
    if (!buf) return -1;
    size_t n;
    int err = 0;
    while ((n = fread(buf, 1, bufsize, in)) > 0) {

        stream_cnt = buf_count(buf, n);
        if (fwrite(buf, 1, n, out) != n) {

            err = -2;
            break;
        }
        printf("\n");
        printf("\nLines: %zu, Words: %zu, Bytes: %zu\n", stream_cnt.lines, stream_cnt.words, stream_cnt.bytes);
        printf("\n");
    }
    free(buf);
    return err; 
}

int copy_file(const char *src, const char *dst, size_t bufsize) {

    FILE *in = fopen(src, "rb");
    if (!in) return -1;
    FILE *out = fopen(dst, "wb");
    if (!out) {

        fclose(in); 
        return -1;
    }
    int ret = copy_stream(in, out, bufsize);
    fclose(in); 
    fclose(out);
    return ret;
}


#endif // COPY_INPUT_TO_OUTPUT_IMPLEMENTATION
#endif // HEADER GUARD