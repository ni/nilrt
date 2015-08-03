#!/bin/bash

set -eE

NIBB_MACHINE=${MACHINE}
NIBB_DISTRO=${DISTRO}
NIBB_DISTVER="3.0"
NIBB_BASE_DIR=${PWD}
NIBB_SOURCE_DIR=${NIBB_BASE_DIR}/sources
NIBB_OECORE_DIR=${NIBB_SOURCE_DIR}/openembedded-core
if [ `expr "${INTERNAL_BUILD}" : '\([Yy][Ee][Ss]\)'` ]; then
	NIBB_INHERIT=own-mirrors
fi

function usage() {
    cat <<EOT
    Usage:  $0 config
            $0 update
            $0 check_source
            $0 info <bitbake_target>
            $0 clean

    Once $0 config is run, build images with
    . \$ENV_FILE (e.g. env-nilrt-xilinx-zynq)
    You can then build images with "bitbake".

    The <bitbake_target> argument is the
    image or package that bitbake build
    information will be gathered for build
    parity comparisons. It must be run from
    a shell that is configured to build the
    target (i.e. you've already source'd the
    environment file from a config command)
EOT
    return 1
}

function update_source() {
    echo "Updating local git repos..."
    git submodule init
    git submodule update --remote --checkout
}

#
# Return:   0 if there's no need to build
#           1 if there's a need to build
function check_source() {
    git submodule init 1> /dev/null
    git submodule update --remote --checkout 1> /dev/null
    changes_to_submodules=`[ -z "$(git submodule summary)" ]`
    git submodule update 1> /dev/null
    return $changes_to_submodules
}

function write_config() {
    NIBB_DISTDIR=`echo ${NIBB_DISTRO} | sed 's#[- ./\#]#_#g'`_`echo ${NIBB_DISTVER} | sed 's#[- ./\#]#_#g'`
    echo Configuring for ${NIBB_MACHINE}...
    cat <<EOF > env-${NIBB_DISTRO}-${NIBB_MACHINE}
export BB_ENV_EXTRAWHITE="BASHOPTS BB_NUMBER_THREADS DISTRO INHERIT MACHINE PARALLEL_MAKE SOURCE_MIRROR_URL USER_CLASSES"
export BB_NUMBER_THREADS="${THREADS:-2}"
export BBPATH="${NIBB_BASE_DIR}/build"
export DISTRO="${NIBB_DISTRO}"
export DISTRO_VERSION="${NIBB_DISTVER}"
export INHERIT="${NIBB_INHERIT}"
export MACHINE="${NIBB_MACHINE}"
export PARALLEL_MAKE="-j ${THREADS:-2}"
export PATH="${NIBB_OECORE_DIR}/scripts:${NIBB_SOURCE_DIR}/bitbake/bin:\${PATH}"
export SOURCE_MIRROR_URL=http://git.natinst.com/snapshots
export USER_CLASSES=""

# mitigates some deliberate races between bash command hashing and sysroot
# cleaning, cf gmane/43740
if [ -n "\$BASH_VERSION" ]; then
	shopt -s checkhash
	export BASHOPTS
fi

EOF
    echo Environment file written to env-${NIBB_DISTRO}-${NIBB_MACHINE}
    echo -e "\n"Source the environment file and build with "bitbake \$target"
}

function get_opts() {
    if [ -z "${MACHINE}" ]; then
        echo -e "Available machines:\n"
        MACHINES=`find */meta* sources/openembedded-core/meta* -path '*/meta*/conf/machine/*' -name "*.conf" 2> /dev/null | sed 's/^.*\///' | sed 's/\.conf//'`
        echo "$MACHINES"
        echo -ne "\nPlease select the desired machine: "
        read NIBB_MACHINE
        while ! echo "$MACHINES" | grep -qP "(^|[ \t])$NIBB_MACHINE([ \t]|$)"; do
            echo -n "Please enter a valid machine name: "
            read NIBB_MACHINE
        done
    fi
    if [ -z "${THREADS}" ]; then
        def_num_threads=`expr $(grep ^processor /proc/cpuinfo | wc -l ) \* 3 / 2`
        echo -n "Parallel bitbake threads and make jobs ($def_num_threads): "
        read THREADS
        re='^[0-9]+$'
        if ! [[ $THREADS =~ $re ]]; then
            echo "Using $def_num_threads"
            THREADS=$def_num_threads
        fi
    fi
    if [ -z "${DISTRO}" ]; then
        echo -e "Available distributions:\n"
        DISTROS=`find sources/meta-* sources/openembedded-core -path '*/conf/distro/*' -name '*.conf' 2> /dev/null | sed 's/.*\///' | sed 's/\.conf//'`
        echo "${DISTROS}"
        echo -ne "\nPlease select the desired distribution: "
        read NIBB_DISTRO
        while ! echo "$DISTROS" | grep -qP "(^|[ \t])$NIBB_DISTRO([ \t]|$)"; do
            echo -n "Please enter a valid machine name: "
            read NIBB_DISTRO
        done
    fi
}

function clean() {
    echo -n "Cleaning build area..."
    rm -rf ${NIBB_BASE_DIR}/build/*
    git checkout ${NIBB_BASE_DIR}/build
    echo "done"
    echo "Cleaning sources..."
    update_source
    echo "done cleaning sources"
}

function get_info() {
    if [ "$#" -ne 2 ]; then
        cat <<EOT > /dev/stderr
*** ERR ***
    Call the "info" command providing exactly one bitbake build target.

EOT
        usage
        return
    fi
    if [ -z "$BBPATH" ]; then
        cat <<EOT > /dev/stderr
*** ERR ***
    Run the info command from a shell that has been configured to build

EOT
        usage
        return
    fi

    IMAGE=$2

    bitbake -e $IMAGE| grep -P "^[A-Za-z_-]+[ \t]*=" | sort | grep -v "`pwd`"  > bitbake_env_filtered_${IMAGE}_${NIBB_MACHINE}.txt

    echo Bitbake environment file available at bitbake_env_filtered_${IMAGE}_${NIBB_MACHINE}.txt
    if [ ! -d ${NIBB_BASE_DIR}/build/tmp_${NIBB_DISTDIR}_${NIBB_MACHINE}-* ]; then
        cat <<EOT
        ${NIBB_BASE_DIR}/build/tmp_${NIBB_DISTDIR}_${NIBB_MACHINE}
*** INFO ***
In order to get a filesystem manifest for the image, please build the image
EOT
    else
         cat <<EOT
Image manifest and version information available at
${NIBB_BASE_DIR}/build/tmp_${NIBB_DISTDIR}_${NIBB_MACHINE}-eglibc/buildhistory/images/${NIBB_MACHINE//-/_}/eglibc/${IMAGE}

EOT
    fi
}

if [ $# -gt 0  -a $# -le 2 ]; then
    case $1 in
        check_source )
            check_source
            exit
            ;;
        update )
            update_source
            exit
            ;;
        config )
            update_source
            get_opts
            write_config
            exit
            ;;
        info )
            get_info "$@"
            exit
            ;;
        clean )
            clean
            exit
            ;;
         -h|--help|--usage )
            usage
            exit
            ;;
         *)
            echo "Unknown command \"$1\""
            usage
            exit
            ;;
    esac
fi

usage

