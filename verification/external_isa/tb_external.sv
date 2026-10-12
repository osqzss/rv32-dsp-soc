`timescale 1ns / 1ps
module tb_external;
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
    integer i, fd, mf, retired = 0;
    reg [8191:0] hex_path, state_path, memory_path;
    initial begin
        if (!$value$plusargs("hex=%s", hex_path) ||
            !$value$plusargs("state=%s", state_path) ||
            !$value$plusargs("memory=%s", memory_path)) $fatal(1, "missing path");
        for (i = 0; i < 4096; i = i + 1) mem[i] = 0;
        $readmemh(hex_path, mem);
        fd = $fopen(state_path, "w");
        mf = $fopen(memory_path, "w");
        if (!fd || !mf) $fatal(1, "output open failed");
        repeat (4) @(posedge clk);
        @(negedge clk) rst_n = 1;
    end
    always @(posedge clk) if (rst_n && !halted) begin
        if (ia >= 16384 || ia[1:0] != 0) $fatal(1, "instruction address outside contract");
        if ((we || insn[6:0] == 7'h03) && da >= 16384)
            $fatal(1, "data address outside test memory");
        $fwrite(fd, "%08x %08x", ia, insn);
        for (i = 0; i < 32; i = i + 1)
            $fwrite(fd, " %08x", dut.regs[i]);
        $fwrite(fd, "\n");
        retired = retired + 1;
        if (insn == 32'h00000073) begin
            $fwrite(fd, "END %0d\n", retired);
            $fwrite(mf, "WORDS 4096\n");
            for (i = 0; i < 4096; i = i + 1)
                $fwrite(mf, "%08x %08x\n", i*4, mem[i]);
            $fwrite(mf, "END 4096\n");
            $fclose(fd); $fclose(mf);
            $display("RTL external stop: %0d observations", retired);
            $finish;
        end else begin
            if (retired >= 20000) $fatal(1, "instruction limit");
            if (we) begin
                if (strb[0]) mem[da >> 2][7:0] <= wd[7:0];
                if (strb[1]) mem[da >> 2][15:8] <= wd[15:8];
                if (strb[2]) mem[da >> 2][23:16] <= wd[23:16];
                if (strb[3]) mem[da >> 2][31:24] <= wd[31:24];
            end
        end
    end
endmodule
