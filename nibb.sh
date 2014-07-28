#!/bin/bash

NIBB_MACHINE=${MACHINE}
NIBB_DISTRO="nilrt"
NIBB_DISTVER="2.0"
NIBB_DISTDIR=`echo ${NIBB_DISTRO} | sed 's#[- ./\#]#_#g'`_`echo ${NIBB_DISTVER} | sed 's#[- ./\#]#_#g'`
NIBB_BASE_DIR=${PWD}
NIBB_SOURCE_DIR=${NIBB_BASE_DIR}/sources
NIBB_OECORE_DIR=${NIBB_SOURCE_DIR}/openembedded-core
NIBB_GIT_REPOS=${NIBB_SOURCE_DIR}/layers.txt

function usage() {
    cat <<EOT
    Usage:  $0 config <machine>
            $0 update
            $0 clean

    Once $0 config is run, build images with
    . \$ENV_FILE (e.g. env-nilrt-xilinx-zynq)
    You can then build images with "bitbake".

    The <machine> argument can be
        xilinx-zynq:    ARM-based NI controllers
        x64:            x64-based NI controllers
EOT
    return 1
}

function update_source() {
    echo "Updating local git repos..."
    pushd ${NIBB_SOURCE_DIR} 1> /dev/null
    while read GIT_REPO GIT_URL GIT_BRANCH GIT_COM ; do
        echo "Updating ${GIT_REPO}..."
        [ -d "${GIT_REPO}" ] ||  git clone ${GIT_URL} ${GIT_REPO}
        pushd ${GIT_REPO} 1> /dev/null
        [ "`git rev-parse --abbrev-ref HEAD`" == "${GIT_BRANCH}" ] || git checkout -b ${GIT_BRANCH} origin/${GIT_BRANCH}
        git reset --hard ${GIT_COM}
        git pull -r --ff-only
        popd 1> /dev/null
    done < ${NIBB_GIT_REPOS}
    popd 1> /dev/null
}

function write_config() {
    echo Configuring for ${NIBB_MACHINE}...
    cat <<EOF > env-${NIBB_DISTRO}-${NIBB_MACHINE}
export BB_ENV_EXTRAWHITE="all_proxy ALL_PROXY BASHOPTS BB_NO_NETWORK BB_NUMBER_THREADS BB_SRCREV_POLICY DISTRO DL_DIR ftp_proxy FTP_PROXY ftps_proxy FTPS_PROXY GIT_PROXY_COMMAND GIT_REPODIR http_proxy HTTP_PROXY https_proxy HTTPS_PROXY _LINUX_GCC_TOOLCHAIN MACHINE no_proxy NO_PROXY PARALLEL_MAKE SCREENDIR SDKMACHINE SOCKS5_PASSWD SOCKS5_USER SOURCE_MIRROR_URL SSH_AGENT_PID SSH_AUTH_SOCK SSTATE_DIR SSTATE_MIRRORS STAMPS_DIR TCLIBC TCMODE USER_CLASSES"
export BB_NUMBER_THREADS="${THREADS:-2}"
export BBFETCH2=True
export BBPATH="${NIBB_BASE_DIR}:${NIBB_OECORE_DIR}/meta"
export BUILD_DIR="${NIBB_BASE_DIR}"
export DISTRO="${NIBB_DISTRO}"
export DISTRO_DIRNAME="${NIBB_DISTDIR}"
export DISTRO_VERSION="${NIBB_DISTVER}"
export GIT_REPODIR="${NIBB_SOURCE_DIR}"
export MACHINE="${NIBB_MACHINE}"
export OE_BUILD_DIR="${NIBB_BASE_DIR}"
export OE_BUILD_TMPDIR="${NIBB_BASE_DIR}/build/tmp_${NIBB_DISTDIR}_${NIBB_MACHINE}"
export OE_SOURCE_DIR="${NIBB_SOURCE_DIR}"
export PARALLEL_MAKE="-j ${THREADS:-2}"
export PATH="${NIBB_OECORE_DIR}/scripts:${NIBB_SOURCE_DIR}/bitbake/bin:${PATH}"
export TOPDIR="${NIBB_BASE_DIR}"
export USER_CLASSES=""
shopt -s checkhash
export BASHOPTS
EOF
    echo Environment file written to env-${NIBB_DISTRO}-${NIBB_MACHINE}
    cat <<EOF > ${NIBB_BASE_DIR}/conf/site.conf
SCONF_VERSION="1"
DL_DIR="${NIBB_BASE_DIR}/downloads"
SSTATE_DIR="${NIBB_BASE_DIR}/build/sstate-cache"
BBFILES?="${NIBB_OECORE_DIR}/meta/recipes-*/*/*.bb"
TMPDIR="${NIBB_BASE_DIR}/build/tmp_${NIBB_DISTDIR}_${NIBB_MACHINE}"
#Set the proxy info here
#HTTP_PROXY="http://\${PROXYHOST}:\${PROXYPORT}"
EOF
    cat <<EOF > ${NIBB_BASE_DIR}/conf/auto.conf
export MACHINE="${NIBB_MACHINE}"
EOF
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
}

function clean() {
    echo -n "Cleaning build area..."
    rm -rf "${NIBB_BASE_DIR}/build" "${NIBB_BASE_DIR}/cache"
    echo "done"
    echo "Cleaning sources..."
    update_source
    echo "done cleaning sources"
}

if [ $# -gt 0  -a $# -le 2 ]; then
    case $1 in
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
            echo I would return info
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

