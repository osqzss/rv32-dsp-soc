`timescale 1ns / 1ps
module tb_core_verify;
    reg clk = 0, rst_n = 0;
    wire [31:0] ia, insn, da, wd, pc, ri, rv;
    wire [3:0] strb;
    wire we, rwe, halted;
    wire [4:0] rd;
    reg [31:0] mem [0:4095];
    wire [31:0] dr = da < 16384 ? mem[da >> 2] : 0;
    assign insn = ia < 16384 ? mem[ia >> 2] : 0;
    rv32i_core dut(clk, rst_n, ia, insn, da, wd, strb, we, dr,
                    pc, ri, rd, rv, rwe, halted);
    always #5 clk = ~clk;
    integer i, fd, memory_fd, nonzero, retired = 0, max_steps;
    reg [8191:0] hex_path, trace_path, memory_path;
    initial begin
        if (!$value$plusargs("hex=%s", hex_path) ||
            !$value$plusargs("trace=%s", trace_path)) $fatal(1, "missing input path");
        if (!$value$plusargs("max=%d", max_steps)) max_steps = 5000;
        for (i = 0; i < 4096; i = i + 1) mem[i] = 0;
        $readmemh(hex_path, mem);
        fd = $fopen(trace_path, "w");
        if (!fd) $fatal(1, "trace open failed");
        if (!$value$plusargs("memory=%s", memory_path)) $fatal(1, "missing memory path");
        memory_fd = $fopen(memory_path, "w");
        if (!memory_fd) $fatal(1, "memory open failed");
        repeat (4) @(posedge clk);
        @(negedge clk) rst_n = 1;
    end
    always @(posedge clk) begin
        if (rst_n && !halted) begin
            if (ia >= 16384) $fatal(1, "instruction address outside test memory");
            if ((we || insn[6:0] == 7'h03) && da >= 16384)
                $fatal(1, "data address outside test memory");
            $fwrite(fd, "%08x %08x %2d %08x\n", pc, ri, rd, rv);
            retired = retired + 1;
            if (retired >= max_steps && insn[6:0] != 7'h73)
                $fatal(1, "instruction limit reached");
        end
        if (rst_n && halted) begin
            $fclose(fd);
            $fwrite(memory_fd, "WORDS 4096\n");
            nonzero = 0;
            for (i = 0; i < 4096; i = i + 1)
                if (mem[i] !== 32'd0) begin
                    $fwrite(memory_fd, "%08x %08x\n", i * 4, mem[i]);
                    nonzero = nonzero + 1;
                end
            $fwrite(memory_fd, "END %0d\n", nonzero);
            $fclose(memory_fd);
            $display("RTL: retired %0d instruction(s), halted", retired);
            $finish;
        end
    end
    always @(posedge clk) if (rst_n && !halted && we && da < 16384) begin
        if (strb[0]) mem[da >> 2][7:0] <= wd[7:0];
        if (strb[1]) mem[da >> 2][15:8] <= wd[15:8];
        if (strb[2]) mem[da >> 2][23:16] <= wd[23:16];
        if (strb[3]) mem[da >> 2][31:24] <= wd[31:24];
    end
endmodule
