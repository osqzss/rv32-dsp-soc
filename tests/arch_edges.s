# Architectural witnesses: legal aligned memory accesses, JALR odd target/alias,
# signedness, shift masking, preserved store lanes and both outcomes of each branch.
    li x1, -16
    srai x2, x1, 31
    srli x3, x1, 31
    srai x4, x1, 0
    li x9, 1
    slli x11, x9, 31
    li x8, 32
    sll x12, x9, x8
    li x8, 33
    sll x13, x9, x8
    li x8, 63
    srl x14, x1, x8
    sra x15, x1, x8
    li x31, 0x2000
    li x10, 0x80ff7f81
    sw x10, 0(x31)
    lb x16, 0(x31)
    lbu x17, 0(x31)
    lh x18, 2(x31)
    lhu x19, 2(x31)
    li x21, 0x55
    sb x21, 1(x31)
    lw x22, 0(x31)
    li x21, 0x1234
    sh x21, 2(x31)
    lw x23, 0(x31)
    addi x0, x0, 99
    addi x24, x0, 7
    sw x0, 8(x31)
    lw x25, 8(x31)
    li x26, -1
    li x27, 1
    li x20, 0
    beq x0, x0, beq_taken
    addi x20, x20, 1
beq_taken:
    beq x26, x27, beq_not
    addi x20, x20, 1
beq_not:
    bne x26, x27, bne_taken
    addi x20, x20, 1
bne_taken:
    bne x0, x0, bne_not
    addi x20, x20, 1
bne_not:
    blt x26, x27, blt_taken
    addi x20, x20, 1
blt_taken:
    blt x27, x26, blt_not
    addi x20, x20, 1
blt_not:
    bge x27, x26, bge_taken
    addi x20, x20, 1
bge_taken:
    bge x26, x27, bge_not
    addi x20, x20, 1
bge_not:
    bltu x27, x26, bltu_taken
    addi x20, x20, 1
bltu_taken:
    bltu x26, x27, bltu_not
    addi x20, x20, 1
bltu_not:
    bgeu x26, x27, bgeu_taken
    addi x20, x20, 1
bgeu_taken:
    bgeu x27, x26, bgeu_not
    addi x20, x20, 1
bgeu_not:
    jal x5, direct_target
    addi x20, x20, 1
direct_target:
    la x6, odd_target
    addi x6, x6, 1
    jalr x7, x6, 0
    addi x20, x20, 1
odd_target:
    addi x28, x7, 0
    la x6, alias_target
    jalr x6, x6, 0
    addi x20, x20, 1
alias_target:
    addi x29, x6, 0
    slt x30, x26, x27
    ecall
