OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS {
  . = 0;
  .text : { *(.text.init) *(.text*) }
  ASSERT(. <= 0x2000, "text exceeds code region")
  . = 0x2000;
  .data : { *(.data*) *(.rodata*) *(.bss*) }
  _end = .;
  ASSERT(. <= 0x4000, "data exceeds test memory")
}
