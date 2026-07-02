// simple_io.h

#ifndef SIMPLE_IO_H
#define SIMPLE_IO_H

#include "io_buffer.h"

#ifdef IO_BUFFER

#define IO_BUFFER_IMPLEMENTATION
#include "io_buffer.h"


// ================= FUNCTION DECLARATIONS =================
// STREAM IO FUNCTIONS 
int copy_stream(FILE *in, FILE *out);
int copy_file(const char *src, const char *dest);

int copy_stream_with_lrbuf(FILE *in, FILE *out);
int copy_file_with_lrbuf(FILE *in, FILE *out);

// ================= SIMPLE I/O IMPLEMENTATION =================
#ifdef SIMPLE_IO_IMPLEMENTATION

int copy_stream(FILE *in, FILE *out) {

    RgBuf rb = rg_new();

    while (!feof(in) && !ferror(in) && !ferror(out)) {
        // 1. 如果环未满，尝试读入数据
        if (rb.count < rb.size) {
            size_t free_space = rb.size - rb.count;
            size_t got = simple_read(&rb, in, free_space);
            if (got == 0 && ferror(in)) return -1;
        }

        // 2. 如果环非空，尝试写出数据
        if (rb.count > 0) {
            size_t wrote = simple_write(&rb, out, rb.count);
            if (wrote == 0 && ferror(out)) return -1;
        }

        // 如果既没有读入也没有写出，且输入未结束，可能是终端等待输入，继续循环
    }

    // 3. 输入结束，清空环中剩余数据
    while (rb.count > 0) {
        size_t wrote = simple_write(&rb, out, rb.count);
        if (wrote == 0) break;
    }
    return 0;
}

int copy_file(const char *src, const char *dest) {

    if (!src || !dest) {

        fprintf(stderr, "ERROR: Source path, destination path or ring buffer is not initialized or empty!");
        return -1;
    }
    FILE *in = fopen(src, "rb");
    if (!in) {

        fprintf(stderr, "ERROR: Failed to open source file: %s", src);
        return -1;
    }
    FILE *out = fopen(dest, "wb");
    if (!out) {

        fprintf(stderr, "ERROR: Failed to open destination file: %s", dest);
        fclose(in);
        return -1;
    }
    int result = copy_stream(in, out);
    fclose(in);
    fclose(out);
    return result;
}
#endif  // SIMPLE_IO_IMPLEMENTATION

#endif  // IO_BUFFER

#ifndef IO_BUFFER

// ================= FUNCTION DECLARATIONS =================
int copy_stream(FILE *in, FILE *out, size_t bufsize);
int copy_file(const char *src, const char *dst, size_t bufsize);

// ================= SIMPLE I/O IMPLEMENTATION =================
#ifdef SIMPLE_IO_IMPLEMENTATION

int copy_stream(FILE *in, FILE *out, size_t bufsize) {
    if (bufsize == 0) bufsize = 65536;
    uint8_t *buf = malloc(bufsize);
    if (!buf) return -ENOMEM;
    
    size_t n;
    int err = 0;
    while ((n = fread(buf, 1, bufsize, in)) > 0) {
        if (fwrite(buf, 1, n, out) != n) {
            err = -EIO;
            break;
        }
    }
    free(buf);
    
    // 区分 EOF 和读错误
    if (ferror(in)) err = -EIO;
    return err;
}

int copy_file(const char *src, const char *dst, size_t bufsize) {
    FILE *in = fopen(src, "rb");
    if (!in) return -errno;
    FILE *out = fopen(dst, "wb");
    if (!out) {
        int saved_errno = errno;
        fclose(in);
        return -saved_errno;
    }
    int ret = copy_stream(in, out, bufsize);
    fclose(in);
    fclose(out);
    return ret;
}
#endif  // SIMPLE_IO_IMPLEMENTATION
#endif  // No IO_BUFFER

#endif // SIMPLE_IO_H