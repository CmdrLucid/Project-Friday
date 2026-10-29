/* z80rt.h -- runtime for the Z80 -> C recompiler (tools/z80recomp.py), docs/SOUND_PLAN.md.  Hand written, contains no game code.
   State, flag helpers and the memory interface of the generated driver step function.  Cycle counts are Z80 cycles (the GPGX core counts master clocks = Z80 cycles * 15). */
#ifndef Z80RT_H
#define Z80RT_H
#include <stdint.h>
typedef struct Z80S {
    uint8_t a, f, b, c, d, e, h, l, a2, f2, b2, c2, d2, e2, h2, l2;
    uint16_t ix, iy, sp, pc;
    uint8_t i, r, iff1, iff2;
    uint32_t cyc;      /* Z80 cycles executed so far */
    uint32_t wait;     /* extra master cycles (68K bus wait states, DMA waits): the Z80's time in master cycles is cyc * 15 + wait */
    int bad;           /* set when pc is not an instruction of the recompiled program */
} Z80S;
extern uint8_t z80rt_rb(Z80S *s, uint16_t addr);
extern void z80rt_wb(Z80S *s, uint16_t addr, uint8_t v);
void z80drv_step(Z80S *s);   /* generated: executes the instruction at s->pc */
#define FS 0x80
#define FZ 0x40
#define FY 0x20
#define FH 0x10
#define FX 0x08
#define FP 0x04
#define FN 0x02
#define FC 0x01
#define RB(a) z80rt_rb(s, (uint16_t)(a))
#define WB(a, v) z80rt_wb(s, (uint16_t)(a), (uint8_t)(v))
#define BC() ((uint16_t)((s->b << 8) | s->c))
#define DE() ((uint16_t)((s->d << 8) | s->e))
#define HL() ((uint16_t)((s->h << 8) | s->l))
#define AF() ((uint16_t)((s->a << 8) | s->f))
#define SET_BC(v) do { uint16_t v_ = (v); s->b = v_ >> 8; s->c = (uint8_t)v_; } while (0)
#define SET_DE(v) do { uint16_t v_ = (v); s->d = v_ >> 8; s->e = (uint8_t)v_; } while (0)
#define SET_HL(v) do { uint16_t v_ = (v); s->h = v_ >> 8; s->l = (uint8_t)v_; } while (0)
#define SET_AF(v) do { uint16_t v_ = (v); s->a = v_ >> 8; s->f = (uint8_t)v_; } while (0)
static inline uint16_t rw_(Z80S *s, uint16_t a) { return (uint16_t)(RB(a) | (RB(a + 1) << 8)); }
static inline void ww_(Z80S *s, uint16_t a, uint16_t v) { WB(a, v & 255); WB(a + 1, v >> 8); }
static inline void push_(Z80S *s, uint16_t v) { s->sp -= 2; ww_(s, s->sp, v); }
static inline uint16_t pop_(Z80S *s) { uint16_t v = rw_(s, s->sp); s->sp += 2; return v; }
static inline uint8_t szxy_(uint8_t r) { return (uint8_t)((r & (FS | FY | FX)) | (r ? 0 : FZ)); }
static inline uint8_t szxyp_(uint8_t r) { return (uint8_t)(szxy_(r) | (__builtin_parity(r) ? 0 : FP)); }
static inline uint8_t add8_(Z80S *s, uint8_t v, int c) { int r = s->a + v + c; uint8_t q = (uint8_t)r; s->f = szxy_(q) | ((s->a ^ v ^ q) & FH) | ((~(s->a ^ v) & (s->a ^ q) & 0x80) ? FP : 0) | (r > 255 ? FC : 0); return q; }
static inline uint8_t sub8_(Z80S *s, uint8_t v, int c) { int r = s->a - v - c; uint8_t q = (uint8_t)r; s->f = szxy_(q) | ((s->a ^ v ^ q) & FH) | (((s->a ^ v) & (s->a ^ q) & 0x80) ? FP : 0) | FN | (r < 0 ? FC : 0); return q; }
static inline void cp8_(Z80S *s, uint8_t v) { uint8_t q = sub8_(s, v, 0); (void)q; s->f = (uint8_t)((s->f & ~(FY | FX)) | (v & (FY | FX))); }
static inline uint8_t inc8_(Z80S *s, uint8_t v) { uint8_t r = (uint8_t)(v + 1); s->f = (uint8_t)((s->f & FC) | szxy_(r) | ((r & 15) == 0 ? FH : 0) | (r == 0x80 ? FP : 0)); return r; }
static inline uint8_t dec8_(Z80S *s, uint8_t v) { uint8_t r = (uint8_t)(v - 1); s->f = (uint8_t)((s->f & FC) | szxy_(r) | ((r & 15) == 15 ? FH : 0) | (r == 0x7F ? FP : 0) | FN); return r; }
static inline uint16_t add16_(Z80S *s, uint16_t x, uint16_t y) { uint32_t r = (uint32_t)x + y; uint16_t q = (uint16_t)r; s->f = (uint8_t)((s->f & (FS | FZ | FP)) | ((q >> 8) & (FY | FX)) | (((x ^ y ^ q) >> 8) & FH) | (r > 0xFFFF ? FC : 0)); return q; }
static inline uint16_t sbc16_(Z80S *s, uint16_t x, uint16_t y) { int32_t r = (int32_t)x - y - (s->f & FC); uint16_t q = (uint16_t)r; s->f = (uint8_t)(((q >> 8) & (FS | FY | FX)) | (q ? 0 : FZ) | (((x ^ y ^ q) >> 8) & FH) | ((((x ^ y) & (x ^ q) & 0x8000) ? FP : 0)) | FN | (r < 0 ? FC : 0)); return q; }
static inline void and8_(Z80S *s, uint8_t v) { s->a &= v; s->f = (uint8_t)(szxyp_(s->a) | FH); }
static inline void or8_(Z80S *s, uint8_t v) { s->a |= v; s->f = szxyp_(s->a); }
static inline void xor8_(Z80S *s, uint8_t v) { s->a ^= v; s->f = szxyp_(s->a); }
static inline void neg_(Z80S *s) { uint8_t o = s->a; s->a = 0; s->a = sub8_(s, o, 0); }
static inline void rlca_(Z80S *s) { uint8_t c = s->a >> 7; s->a = (uint8_t)((s->a << 1) | c); s->f = (uint8_t)((s->f & (FS | FZ | FP)) | (s->a & (FY | FX)) | c); }
static inline void rrca_(Z80S *s) { uint8_t c = s->a & 1; s->a = (uint8_t)((s->a >> 1) | (c << 7)); s->f = (uint8_t)((s->f & (FS | FZ | FP)) | (s->a & (FY | FX)) | c); }
static inline void rla_(Z80S *s) { uint8_t c = s->a >> 7; s->a = (uint8_t)((s->a << 1) | (s->f & FC)); s->f = (uint8_t)((s->f & (FS | FZ | FP)) | (s->a & (FY | FX)) | c); }
static inline void rra_(Z80S *s) { uint8_t c = s->a & 1; s->a = (uint8_t)((s->a >> 1) | ((s->f & FC) << 7)); s->f = (uint8_t)((s->f & (FS | FZ | FP)) | (s->a & (FY | FX)) | c); }
static inline uint8_t rr8_(Z80S *s, uint8_t v) { uint8_t c = v & 1, r = (uint8_t)((v >> 1) | ((s->f & FC) << 7)); s->f = (uint8_t)(szxyp_(r) | c); return r; }
static inline uint8_t srl8_(Z80S *s, uint8_t v) { uint8_t c = v & 1, r = (uint8_t)(v >> 1); s->f = (uint8_t)(szxyp_(r) | c); return r; }
static inline void bit_(Z80S *s, int n, uint8_t v) { uint8_t t = v & (1 << n); s->f = (uint8_t)((s->f & FC) | FH | (t ? 0 : (FZ | FP)) | (t & FS) | (v & (FY | FX))); }
#define SWAP8(x, y) do { uint8_t t_ = x; x = y; y = t_; } while (0)
#endif
