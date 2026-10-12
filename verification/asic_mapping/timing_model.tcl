read_liberty $::env(TIMING_LIBRARY)
read_verilog $::env(TIMING_NETLIST)
link_design rv32i_core
read_sdc baseline-portable.sdc
report_units
puts "COVERAGE_PASS [check_setup -verbose]"
puts "BEGIN_CLOCK_MODEL"
report_clock_properties [all_clocks]
puts "END_CLOCK_MODEL"
puts "BEGIN_NET_MODEL"
report_net -digits 6 clk
if {$::env(TIMING_ARM) eq "baseline"} {
  foreach net [get_nets -of_objects [get_pins _07480_/ZN]] {
    report_net -digits 6 [get_full_name $net]
  }
}
puts "END_NET_MODEL"
puts "BEGIN_DESIGN_RULES"
report_check_types -max_slew -max_capacitance -violators
puts "END_DESIGN_RULES"
puts "BEGIN_WORST_PATH"
report_checks -path_delay max -group_path_count 1 -digits 6
puts "END_WORST_PATH"
puts "BEGIN_REGISTER_PATH"
report_checks -path_delay max -from [all_registers -clock core_clk -clock_pins] -to [all_registers -clock core_clk -data_pins] -group_path_count 1 -digits 6
puts "END_REGISTER_PATH"
puts "BEGIN_MIN_PATH"
report_checks -path_delay min -group_path_count 1 -digits 6
puts "END_MIN_PATH"
puts "BEGIN_MIN_REGISTER_PATH"
report_checks -path_delay min -from [all_registers -clock core_clk -clock_pins] -to [all_registers -clock core_clk -data_pins] -group_path_count 1 -digits 6
puts "END_MIN_REGISTER_PATH"
exit
