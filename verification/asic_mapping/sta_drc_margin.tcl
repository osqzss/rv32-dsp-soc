read_liberty $::env(TIMING_LIBRARY)
read_verilog $::env(TIMING_NETLIST)
link_design rv32i_core
read_sdc baseline-portable.sdc
puts "BEGIN_ALL_DESIGN_RULE_CHECKS"
report_check_types -max_slew -max_capacitance -digits 6
puts "END_ALL_DESIGN_RULE_CHECKS"
exit
