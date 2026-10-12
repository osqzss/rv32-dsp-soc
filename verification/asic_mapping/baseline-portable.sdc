create_clock -name core_clk -period 10 [get_ports clk]
set_clock_uncertainty 0.1 [get_clocks core_clk]
set_clock_transition 0.1 [get_clocks core_clk]
set data_inputs {}
foreach port [all_inputs] {
  if {[get_full_name $port] ne "clk"} {lappend data_inputs $port}
}
set_input_delay 2 -clock core_clk $data_inputs
set_input_transition 0.1 $data_inputs
set_output_delay 2 -clock core_clk [all_outputs]
# Nangate45 Liberty uses fF: 10 fF = 0.01 pF.
set_load 10 [all_outputs]
# Synchronous setup study excludes asynchronous-reset recovery/removal.
set_false_path -from [get_ports rst_n]
