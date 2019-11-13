mode con: cols=120 lines=30
set mem_MB="${VM_MEM_SIZE_MB}"
set "qemu_bin=C:\Program Files\qemu\qemu-system-x86_64.exe"
set "qemu_extra_args="
IF NOT [%1] == [] (
	set "qemu_extra_args=%qemu_extra_args% -netdev tap,ifname="%1",id=nilrt_net0 -device e1000,netdev=nilrt_net0"
)

"%qemu_bin%" ^
	-cpu "Nehalem-v2" -smp cpus=1 ^
	-accel hax ^
	-m %mem_MB% ^
	-nographic ^
	-bios "%~dp0%OVMF\OVMF_CODE.fd" ^
	-drive file="%~dp0%${VM_NAME}.qcow2" ^
	%qemu_extra_args%
