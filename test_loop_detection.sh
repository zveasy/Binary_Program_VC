#!/bin/bash

# Compile infinite loop binary (clearly intentional)
gcc infinite_loop.c -o firmware/infinite_loop_test.bin

# Create and compile simple "hello world" binary without loops
echo -e '#include <stdio.h>\nint main() { puts("Hello, World!"); return 0; }' > hello_world.c
gcc hello_world.c -o firmware/hello_world_test.bin

# Run infinite loop test explicitly
python3 rda_disassembler_enhanced.py firmware/infinite_loop_test.bin
echo "Infinite loop test result (expecting loop detected):"
grep "infinite loop" firmware/disassembly.log || echo "❌ No loop detected (unexpected)"

# Run hello_world test explicitly (should not detect loops)
python3 rda_disassembler_enhanced.py firmware/hello_world_test.bin
echo "Hello World test result (expecting NO loop detected):"
if grep -qi "infinite loop detected" firmware/disassembly.log; then
    echo "❌ Unexpected infinite loop detected in hello_world binary!"
else
    echo "✅ No infinite loops detected (expected)"
fi