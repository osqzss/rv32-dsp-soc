/* Adapted bare test environment. Upstream test bodies/macros are unchanged. */
#define RVTEST_RV32U
#define RVTEST_RV64U RVTEST_RV32U
#define TESTNUM x3
#define RVTEST_CODE_BEGIN .section .text.init; .globl _start; _start:
#define RVTEST_CODE_END
#define RVTEST_PASS li x3, 1; ecall
#define RVTEST_FAIL slli x3, x3, 1; ori x3, x3, 1; ecall
#define RVTEST_DATA_BEGIN .section .data; .balign 16; .globl begin_signature; begin_signature:
#define RVTEST_DATA_END .globl end_signature; end_signature:
