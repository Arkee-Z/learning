// ring.h

#ifndef RING_H
#define RING_H

#include <stdio.h>
#include <stdlib.h>

// ================= CONSTANTS =================
#define SIZE_1K 1024                
#define SIZE_4K 4096
#define SIZE_8K 8192
#define SIZE_16K 16384
#define SIZE_32K 32768
#define SIZE_64K 65536

#define SIZE_1K 1024                
#define SIZE_4K 4096
#define SIZE_8K 8192
#define SIZE_16K 16384
#define SIZE_32K 32768
#define SIZE_64K 65536

// ================= STRUCTURE RING =================
#define _RING_BODY(_size) \
    struct { \
        uint8_t data[_size]; \
        size_t ir, iw, mark, count; \
        size_t size; \
    }

#define _RING_ASSERT(_size) \
    _Static_assert((_size) > 0 && ((_size) & ((_size) - 1)) == 0, \
        "Ring buffer size must be a power of two and greater than zero.")

#define _RING_DEF(_type_name, _size) \
    _RING_ASSERT(_size); \
    typedef _RING_BODY(_size) _type_name;

#define Ring(_type_name, _size) _RING_DEF(_type_name, _size);

// base ring
Ring(ring_t, SIZE_1K)
// middle ring
Ring(ring4_t, SIZE_4K)
Ring(ring8_t, SIZE_8K)
// large ring
Ring(ring16_t, SIZE_16K)
Ring(ring32_t, SIZE_32K)
Ring(ring64_t, SIZE_64K)

// 初始化 
#define ring_init(rb) \
    do { \
        typeof(*(rb)) *r = (rb); \
        r->ir = r->iw = r->mark = r->count = 0; \
        r->size = sizeof(r->data); \
    } while(0)

// 单个字节操作 
#define ring_push(rb, c) \
    do { \
        typeof(*(rb)) *r = (rb); \
        if (r->count == r->size) break; \
        r->data[r->iw & (r->size - 1)] = (uint8_t)(c); \
        r->iw++; \
        r->count++; \
    } while(0)

#define ring_pop(rb, out) \
    do { \
        typeof(*(rb)) *r = (rb); \
        if (r->count == 0) break; \
        *(out) = r->data[r->ir & (r->size - 1)]; \
        r->ir++; \
        r->count--; \
    } while(0)

// 偷看（不移动读指针） 
#define ring_peek(rb) \
    ({ \
        typeof(*(rb)) *r = (rb); \
        int _c = -1; \
        if (r->count > 0) { \
            _c = r->data[r->ir & (r->size - 1)]; \
        } \
        _c; \
    })

// 状态查询 
#define ring_is_empty(rb) \
    ({ \
        typeof(*(rb)) *r = (rb); \
        (r->count == 0); \
    })

#define ring_is_full(rb) \
    ({ \
        typeof(*(rb)) *r = (rb); \
        (r->count == r->size); \
    })

#define ring_available(rb) \
    ({ \
        typeof(*(rb)) *r = (rb); \
        (r->count); \
    })

// 标记和回退（回溯核心） 
#define ring_mark(rb) \
    do { \
        typeof(*(rb)) *r = (rb); \
        r->mark = r->ir; \
    } while(0)

#define ring_rewind(rb) \
    do { \
        typeof(*(rb)) *r = (rb); \
        r->ir = r->mark; \
        r->count = r->iw - r->ir; \
    } while(0)

#endif