
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.NOTPARALLEL:

# CUSTOMIZABLE PARAMETERS
DISK_SIZE_MB ?= 4096
MEMORY_MB ?= 1024
VM_NAME ?= nilrt-x64-qemu
PRIMARY_DISK = $(VM_NAME).qcow2

# DIRECTORIES
bbdir ?= ../../../build
bbdeploy = $(bbdir)/tmp-glibc/deploy/images/x64
builddir_tmp = $(bbdir)/$(VM_NAME)-tmp
builddir_zip_contents = $(builddir_tmp)/$(VM_NAME)

# BINARIES
BITBAKE ?= $(PYREX_RUN) bitbake
GENISOIMAGE ?= $(PYREX_RUN) genisoimage
PYREX_RUN ?= pyrex-run
QEMU_SYSTEM_X86_64 ?= $(PYREX_RUN) qemu-system-x86_64
ZIP ?= zip


# ==============================================================================
# REAL TARGETS
# ==============================================================================

$(builddir_tmp)/ni_provisioning.answers : ni_provisioning.answers
	mkdir -p $(@D)
	cp $< $@
	chmod 0644 "$@"


$(builddir_tmp)/ni_provisioning.answers.iso : $(builddir_tmp)/ni_provisioning.answers
	$(GENISOIMAGE) -quiet \
		-input-charset utf-8 \
		-full-iso9660-filenames \
		-o "$@" \
		"$<"
	chmod 0644 "$@"


$(bbdeploy)/ovmf.code.fd $(bbdeploy)/ovmf.vars.fd &:
	$(BITBAKE) -C deploy ovmf


$(builddir_zip_contents)/OVMF/%.fd : $(bbdeploy)/%.fd
	mkdir -p $(@D)
	cp $< $@


$(builddir_zip_contents)/start-vm.% : start-vm.%.in
	mkdir -p $(@D)
	install -c $< $@
	sed -i "s%\$${PRIMARY_DISK}%$(PRIMARY_DISK)%g" "$@"
	sed -i "s%\$${VM_MEM_SIZE_MB}%$(MEMORY_MB)%g" "$@"


recovery_iso = $(bbdeploy)/nilrt-recovery-media-x64.iso
$(recovery_iso) :
	$(BITBAKE) nilrt-recovery-media


primary_disk_path = $(builddir_zip_contents)/$(PRIMARY_DISK)
vmdeps = \
	$(builddir_tmp)/ni_provisioning.answers \
	$(builddir_zip_contents)/OVMF/ovmf.code.fd \
	$(builddir_zip_contents)/OVMF/ovmf.vars.fd \
	$(builddir_zip_contents)/start-vm.bat \
	$(builddir_zip_contents)/start-vm.sh \
	$(recovery_iso) \
	$(builddir_tmp)/ni_provisioning.answers.iso
$(primary_disk_path) : $(vmdeps)
	rm -f "$@"
	qemu-img create -f qcow2 "$@" "$(DISK_SIZE_MB)""M"
	chmod 0644 "$@"
	$(QEMU_SYSTEM_X86_64) \
		$$($(PYREX_RUN) sh -c "test -w /dev/kvm 2>/dev/null && echo -enable-kvm") \
		-cpu Nehalem,check=false \
		-smp cpus=1 \
		-m $(MEMORY_MB) \
		-nographic \
		-drive if=pflash,format=raw,readonly=on,file="$(builddir_zip_contents)/OVMF/ovmf.code.fd" \
		-drive if=pflash,format=raw,file="$(builddir_zip_contents)/OVMF/ovmf.vars.fd" \
		-drive file="$(primary_disk_path)",media=disk,index=0 \
		-drive file="$(recovery_iso)",media=cdrom,readonly=on,index=1 \
		-drive file="$(builddir_tmp)/ni_provisioning.answers.iso",media=cdrom,readonly=on,index=2


$(bbdir)/$(VM_NAME).zip : $(primary_disk_path) $(vmdeps) $(recovery_iso)
	rm -f "$@"
	(cd "$(builddir_zip_contents)/.." && $(ZIP) --quiet --recurse-paths "$(abspath $@)" "$(notdir $(builddir_zip_contents))")
	chmod 0644 "$@"



# ==============================================================================
# PHONY TARGETS
# ==============================================================================

all : $(bbdir)/$(VM_NAME).zip
.PHONY : all


clean :
	rm -rf $(builddir_zip_contents)
	rm -f $(bbdir)/$(VM_NAME).zip
	rm -rf $(builddir_tmp)
.PHONY : clean


help :
	@echo "NILRT VM Resources Makefile"
	@echo "============================"
	@echo ""
	@echo "PURPOSE:"
	@echo "  This Makefile builds a QEMU VM package for testing NILRT images."
	@echo "  It creates a bootable VM with OVMF UEFI firmware, a primary disk,"
	@echo "  and the NILRT recovery media pre-configured."
	@echo ""
	@echo "PREREQUISITES:"
	@echo "  You must source the ni-oe-init-build-env script from the project root"
	@echo "  before running this Makefile:"
	@echo "    $$ source ../../../ni-oe-init-build-env"
	@echo ""
	@echo "CUSTOMIZABLE PARAMETERS:"
	@echo "  DISK_SIZE_MB      Size of the VM disk in megabytes (default: 4096)"
	@echo "  MEMORY_MB         VM memory size in megabytes (default: 1024)"
	@echo "  VM_NAME           Name of the VM directory and zip file (default: nilrt-x64-qemu)"
	@echo "  PRIMARY_DISK      Name of the primary disk image (default: nilrt-x64-qemu.qcow2)"
	@echo ""
	@echo "USAGE:"
	@echo "  make              Build the VM package (creates $(VM_NAME).zip)"
	@echo "  make clean        Remove all generated files"
	@echo "  make help         Display this help message"
	@echo ""
	@echo "EXAMPLE:"
	@echo "  $$ make DISK_SIZE_MB=8192 MEMORY_MB=2048"
	@echo ""
.PHONY : help
