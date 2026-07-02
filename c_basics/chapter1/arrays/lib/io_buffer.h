// io_buffer.h

#ifndef IOBUFFER_H
#define IOBUFFER_H

#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "ring.h"


// ================= CONSTANTS =================
#define BASECAP 16                   // 基础容量（块数）
#define BASESIZ 4096                 // 每块大小（字节）
#define EXPAND 2                     // 扩容因子
#define INITSIZ (BASESIZ * BASECAP)  // 初始总字节数 = 65536

// ================ STRUCTURES =================
typedef struct DynamicArrayInner {
    size_t cap;             // 当前容量（块数）
    size_t size;            // 当前总字节数（= cap * BASESIZ）
    uint8_t *data;          // 堆指针, 指向动态分配的内存数据块
} DArrInner;                // 动态数组内部结构体

typedef struct DynamicArray {
    size_t pos;             // 当前读写位置（字节偏移）
    size_t len;             // 有效数据长度（字节数）
    DArrInner inner;
} DArr;                     // 动态数组

typedef DArr LrBuf;
typedef ring_t RgBuf;

// ================= FUNCTION DECLARATIONS =================
LrBuf lb_new(void);
LrBuf lb_expand(LrBuf lb);
LrBuf lb_append(LrBuf lb, const uint8_t *data, size_t data_len);
LrBuf lb_copy(const LrBuf *src);
int lb_delete(LrBuf *lb);

int rg_reset(RgBuf *rb);
RgBuf rg_new(void);
int rg_delete(RgBuf *rb);

int rg_push(RgBuf *rb, uint8_t byte);
int rg_pop(RgBuf *rb, uint8_t *byte);
int rg_peek(const RgBuf *rb, uint8_t *byte);

int rg_push_bytes(RgBuf *rb, const uint8_t *src, size_t n);
int rg_pop_bytes(RgBuf *rb, uint8_t *dest, size_t n);
int rg_peek_bytes(const RgBuf *rb, uint8_t *dest, size_t n);

int rg_mark(RgBuf *rb);
int rg_rewind(RgBuf *rb);

int rg_is_empty(const RgBuf *rb);
int rg_is_full(const RgBuf *rb);

size_t rg_available(const RgBuf *rb);

// SIMPLE R/W FUNCTIONS 
static inline size_t simple_read(RgBuf *rb, FILE *in, size_t n);
static inline size_t simple_write(RgBuf *rb, FILE *out, size_t n);

// STAGING BUFFER R/W FUNCTIONS
static inline int load_to_buffer(FILE *in, LrBuf *lb);
static inline int write_from_buffer(FILE *out, LrBuf *lb);


#endif  // IOBUFFER_H

// ============ STB IMPLEMENTATION ============
#ifdef IO_BUFFER_IMPLEMENTATION

// ============ LRBUF IMPLEMENTATION ============
LrBuf lb_new(void) {

    LrBuf lb = {0}; // 初始化为零，确保所有字段都被正确初始化
    lb.inner.data = malloc(INITSIZ);
    if (!lb.inner.data) {

        lb.inner.cap = 0;
        lb.inner.size = 0;
        fprintf(stderr, "ERROR: Memory allocation failed!");
        return lb;
    }
    memset(lb.inner.data, 0, INITSIZ);
    lb.inner.cap = BASECAP;
    lb.inner.size = INITSIZ;
    lb.pos = 0;
    lb.len = 0;
    return lb;
}

LrBuf lb_expand(LrBuf lb) {

    if (!lb.inner.data) {

        fprintf(stderr,"ERROR: Data source is not initialized or empty!");
        return lb;
    }
    size_t old_cap = lb.inner.cap;
    size_t old_size = lb.inner.size;
    size_t new_cap = old_cap * EXPAND;
    size_t new_size = new_cap * BASESIZ;
    uint8_t *new_data = realloc(lb.inner.data, new_size);
    if (!new_data) {

        fprintf(stderr, "ERROR: Memory reallocation failed!");
        return lb;
    }
    memset(new_data + old_size, 0, (new_size - old_size));
    lb.inner.data = new_data;
    lb.inner.cap = new_cap;
    lb.inner.size = new_size;
    return lb;
}

LrBuf lb_append(LrBuf lb, const uint8_t *data, size_t data_len) {

    if (!lb.inner.data) {
        
        fprintf(stderr, "ERROR: Data source is not initialized or empty!");
        return lb;
    }
    while (lb.len + data_len > lb.inner.size) {

        lb = lb_expand(lb);
        if (!lb.inner.data) {

            fprintf(stderr, "ERROR: Buffer expansion failed!");
            return lb; // 扩容失败，返回原始缓冲区
        }
    }
    memcpy(lb.inner.data + lb.len, data, data_len);
    lb.len += data_len;
    return lb;
}

LrBuf lb_copy(const LrBuf *src) {

    LrBuf dst = {0};
    if (!src || !src->inner.data || src->inner.size == 0) {
        
        fprintf(stderr, "ERROR: Data source is not initialized or empty!");
        return dst;
    }
    dst = *src; // 浅拷贝固定字段
    dst.inner.data = malloc(src->inner.size);
    if (!dst.inner.data) {
        
        fprintf(stderr, "ERROR: Memory allocation failed!");
        return dst;
    }
    memcpy(dst.inner.data, src->inner.data, src->inner.size);
    return dst;
}

int lb_delete(LrBuf *lb) {

    if (!lb || !lb->inner.data) {
        
        fprintf(stderr, "ERROR: Data source is not initialized or empty!");
        return -1;
    }

    free(lb->inner.data);
    lb->inner.data = NULL;
    lb->inner.cap = 0;
    lb->inner.size = 0;
    lb->pos = 0;
    lb->len = 0;
    return 0;
}

static inline int load_to_buffer(FILE *in, LrBuf *lb) {

    if (!in || !lb) {

        fprintf(stderr, "ERROR: Input stream or dynamic array buffer is not initialized or empty!");
        return -1;
    }
    *lb = lb_new();
    int err = 0;
    size_t bytes_read;
    while ((bytes_read = fread(lb->inner.data + lb->len, 1, BASESIZ, in)) > 0) {
        lb->len += bytes_read;
        if (lb->len >= lb->inner.size) {
            *lb = lb_expand(*lb);
            if (!lb->inner.data) {
                fprintf(stderr, "ERROR: Buffer expansion failed!");
                return -1;
            }
        }
    }
    if (ferror(in)) {
        fprintf(stderr, "ERROR: Error reading from input stream!");
        err = -1;
    }
    return err;
}

static inline int write_from_buffer(FILE *out, LrBuf *lb) {

    if (!out || !lb || !lb->inner.data) {

        fprintf(stderr, "ERROR: Output stream or dynamic array buffer is not initialized or empty!");
        return -1;
    }
    size_t bytes_written = fwrite(lb->inner.data, 1, lb->len, out);
    if (bytes_written != lb->len) {
        fprintf(stderr, "ERROR: Mismatch in bytes written from buffer!");
        return -1;
    }
    lb_delete(lb);
    return 0;
}

// ============ RING BUFFER IMPLEMENTATION ============
RgBuf rg_new(void) {

    RgBuf rb = {0};
    int ret = rg_reset(&rb);
    if (ret == -1) {
        fprintf(stderr, "ERROR: Fail to reset ring buffer!");  
        return rb;
    }
    return rb;
}

int rg_reset(RgBuf *rb) {

    if (!rb) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");  
        return -1;
    }
    ring_init(rb);
    memset(rb->data, 0, sizeof(rb->data));
    return 0;
}

int rg_delete(RgBuf *rb) {

        if (!rb) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");  
        return -1;
    }
    rb->ir = rb->iw = rb->mark = rb->count = 0;
    rb->size = 0;
    memset(rb->data, 0, sizeof(rb->data));
    return 0;
}

int rg_push(RgBuf *rb, uint8_t byte) {

    if (!rb) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");
        return -1;
    }

    if (rb->count >= rb->size) {

        fprintf(stderr, "ERROR: Ring buffer is full!");
        return -1;
    }
    ring_push(rb, byte);
    return 0;
}

int rg_pop(RgBuf *rb, uint8_t *byte) {

    if (!rb || !byte) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");
        return -1;
    }

    if (rb->count == 0) {

        fprintf(stderr, "ERROR: Ring buffer is empty!");
        return -1;
    }
    ring_pop(rb, byte);
    return 0;
}

int rg_peek(const RgBuf *rb, uint8_t *byte) {

    if (!rb || !byte) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");
        return -1;
    }

    if (rb->count == 0) {

        fprintf(stderr, "ERROR: Ring buffer is empty!");
        return -1;
    }
    ring_peek(rb);
    return 0;
}

int rg_push_bytes(RgBuf *rb, const uint8_t *src, size_t n) {
    
    if (rb == NULL || src == NULL) {

        fprintf(stderr, "ERROR: Ring buffer or source is not initialized or empty!");
        return -1;
    }
    if (n > rb->size - rb->count) {

        fprintf(stderr, "ERROR: Not enough space in ring buffer to push %zu bytes!", n);
        return -1;
    }
    size_t mask = rb->size - 1;
    size_t iw = rb->iw;
    size_t first_chunk = rb->size - (iw & mask);
    if (first_chunk > n) first_chunk = n;
    memcpy(&rb->data[iw & mask], src, first_chunk);
    if (n > first_chunk) {

        memcpy(&rb->data[0], src + first_chunk, n - first_chunk);
    }
    rb->iw += n;
    rb->count += n;
    return 0; 
}

int rg_pop_bytes(RgBuf *rb, uint8_t *dest, size_t n) {

    if (rb == NULL || dest == NULL) {

        fprintf(stderr, "ERROR: Ring buffer or destination is not initialized or empty!");
        return -1;
    }
    if (n > rb->count) {

        fprintf(stderr, "ERROR: Not enough data in ring buffer to pop %zu bytes!", n);
        return -1;
    }
    size_t mask = rb->size - 1;
    size_t ir = rb->ir;
    size_t first_chunk = rb->size - (ir & mask);
    if (first_chunk > n) first_chunk = n;
    memcpy(dest, &(rb->data[ir & mask]), first_chunk);
    if (n > first_chunk) {

        memcpy(dest + first_chunk, &(rb->data[0]), n - first_chunk);
    }
    rb->ir += n;
    rb->count -= n;
    return 0; 
}

int rg_peek_bytes(const RgBuf *rb, uint8_t *dest, size_t n) {

    if (rb == NULL || dest == NULL) {

        fprintf(stderr, "ERROR: Ring buffer or destination is not initialized or empty!");
        return -1;
    }
    if (n > rb->count) {

        fprintf(stderr, "ERROR: Not enough data in ring buffer to peek %zu bytes!", n);
        return -1;
    }
    size_t mask = rb->size - 1;
    size_t ir = rb->ir;
    size_t first_chunk = rb->size - (ir & mask);
    if (first_chunk > n) first_chunk = n;
    memcpy(dest, &(rb->data[ir & mask]), first_chunk);
    if (n > first_chunk) {

        memcpy(dest + first_chunk, &(rb->data[0]), n - first_chunk);
    }
    return 0; 
}

int rg_mark(RgBuf *rb) {

    if (rb == NULL) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");
        return -1;
    }
    ring_mark(rb);
    return 0;
}

int rg_rewind(RgBuf *rb) {

    if (rb == NULL) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");
        return -1;
    }
    ring_rewind(rb);
    return 0;
}

int rg_is_empty(const RgBuf *rb) {

    if (rb == NULL) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");
        return -1;
    }
    return rb->count == 0;
}

int rg_is_full(const RgBuf *rb) {

    if (rb == NULL) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");
        return -1;
    }
    return rb->count == rb->size;
}

size_t rg_available(const RgBuf *rb) {

    if (rb == NULL) {

        fprintf(stderr, "ERROR: Ring buffer is not initialized or empty!");
        return -1;
    }
    return rb->size - rb->count;
}

// ==================== 从流读入环（生产者） ====================
static inline size_t simple_read(RgBuf *rb, FILE *in, size_t n) {

    if (n == 0) return 0;
    if (rb->count == rb->size) return 0;  // 环满了，无法写入，非阻塞返回0

    size_t total = 0;
    size_t mask = rb->size - 1;

    while (total < n && rb->count < rb->size) {
        size_t offset = rb->iw & mask;
        size_t space_to_end = rb->size - offset;
        size_t free_space = rb->size - rb->count;
        size_t to_read = n - total;
        if (to_read > free_space) to_read = free_space;
        if (to_read > space_to_end) to_read = space_to_end;

        if (to_read == 0) break;

        size_t got = fread(rb->data + offset, 1, to_read, in);
        if (got == 0) {
            // 0 表示 EOF 或暂时无数据（非阻塞流），直接返回已读总数
            return total;
        }

        rb->iw += got;
        rb->count += got;
        total += got;
    }
    return total;
}

// ==================== 从环写出到流（消费者） ====================
static inline size_t simple_write(RgBuf *rb, FILE *out, size_t n) {

    if (n == 0) return 0;
    if (rb->count == 0) return 0;  // 环空了，无法读取，非阻塞返回0

    size_t total = 0;
    size_t mask = rb->size - 1;

    while (total < n && rb->count > 0) {
        size_t offset = rb->ir & mask;
        size_t space_to_end = rb->size - offset;
        size_t avail = rb->count;
        size_t to_write = n - total;
        if (to_write > avail) to_write = avail;
        if (to_write > space_to_end) to_write = space_to_end;

        if (to_write == 0) break;

        size_t written = fwrite(rb->data + offset, 1, to_write, out);
        if (written == 0) {
            // 写入失败，返回已写总数
            return total;
        }

        rb->ir += written;
        rb->count -= written;
        total += written;
    }
    return total;
}

#endif  //IO_BUFFER_IMPLEMENTATION
