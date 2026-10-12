#!/usr/bin/env bash
# Run from verification/external_isa in a clean checkout of the recorded base.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p upstream tools logs
exec > >(tee logs/bootstrap.log) 2>&1
date -Is
git clone https://github.com/riscv-software-src/riscv-tests.git upstream/riscv-tests
git -C upstream/riscv-tests checkout --detach 7b68f7b91f827f8d94cc1c57ff123752c5c8f704
git clone https://github.com/sysprog21/rv32emu.git upstream/rv32emu
git -C upstream/rv32emu checkout --detach a5b5f9217fb2b4d8a73fcf4e572aa90ccc33f07c
git clone https://github.com/sysprog21/Kconfiglib.git upstream/rv32emu/tools/kconfig
git -C upstream/rv32emu/tools/kconfig checkout --detach 6d9102abd55b614d3c6133529ffa40dbea7fd2cf
git -C upstream/rv32emu submodule update --init src/mini-gdbstub
test "$(git -C upstream/rv32emu/src/mini-gdbstub rev-parse HEAD)" = 8aefbcda5311c2eeb49ae6c457e4957f5c232863
(cd tools; apt-get download binutils-riscv64-unknown-elf=2.42-1ubuntu1+6)
echo 'd42d42efdaa0563155d0e1263675852255b20864cc525db9265247a5dec2ce30  tools/binutils-riscv64-unknown-elf_2.42-1ubuntu1+6_amd64.deb' | sha256sum -c
dpkg-deb -x tools/binutils-riscv64-unknown-elf_2.42-1ubuntu1+6_amd64.deb tools/binutils
git -C upstream/rv32emu apply ../../reference-observation-v2.patch
make -C upstream/rv32emu mini_defconfig
make -C upstream/rv32emu -j4 ENABLE_EXT_M=0 ENABLE_EXT_A=0 ENABLE_EXT_F=0 ENABLE_EXT_C=0 ENABLE_Zicsr=0 ENABLE_Zifencei=0 ENABLE_JIT=0 ENABLE_MOP_FUSION=0 ENABLE_BLOCK_CHAINING=0 ENABLE_LTO=0 ENABLE_GDBSTUB=1
export PATH=$PWD/tools/binutils/usr/bin:/home/toshn/tools/oss-cad-suite/bin:$PATH
export PYTHONDONTWRITEBYTECODE=1
python3 run.py --test add --out runs/development-add
python3 controls.py runs/controls
python3 extra_controls.py
python3 run.py --out runs/external-suite
