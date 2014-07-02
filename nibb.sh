#!/bin/bash

NIBB_MACHINE=${MACHINE:-"xilinx-zynq"}
NIBB_DISTRO="nilrt"
NIBB_DISTVER="2.0"
NIBB_DISTDIR=`echo ${NIBB_DISTRO} | sed 's#[- ./\#]#_#g'`_`echo ${NIBB_DISTVER} | sed 's#[- ./\#]#_#g'`
NIBB_ENV_FILE=env-${NIBB_DISTRO}-${NIBB_MACHINE}
NIBB_BASE_DIR=${PWD}
NIBB_SOURCE_DIR=${NIBB_BASE_DIR}/sources
NIBB_OECORE_DIR=${NIBB_SOURCE_DIR}/openembedded-core
NIBB_GIT_REPOS=${NIBB_SOURCE_DIR}/layers.txt

function usage() {
    cat <<EOT
    Usage:  $0 config <machine>
            $0 update
            $0 info
            $0 clean

    Once $0 config is run, build images with
    . ${NIBB_ENV_FILE}
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
        [ -d "${GIT_REPO}" ] ||  git clone ${GIT_URL}
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
    cat <<EOF > ${NIBB_ENV_FILE}
export BBFETCH2=True
export DISTRO="${NIBB_DISTRO}"
export DISTRO_VERSION="${NIBB_DISTVER}"
export DISTRO_DIRNAME="${NIBB_DISTDIR}"
export OE_BUILD_DIR="${NIBB_BASE_DIR}"
export TOPDIR="${NIBB_BASE_DIR}"
export BUILD_DIR="${NIBB_BASE_DIR}"
export OE_BUILD_TMPDIR="${NIBB_BASE_DIR}/build/tmp_${NIBB_DISTDIR}"
export OE_SOURCE_DIR="${NIBB_SOURCE_DIR}"
#Do we actually need this one?
export OE_LAYERS_TXT="${NIBB_SOURCE_DIR}/layers.txt"
export PATH="${NIBB_OECORE_DIR}/scripts:${NIBB_SOURCE_DIR}/bitbake/bin:${PATH}"
export BB_ENV_EXTRAWHITE="MACHINE DISTRO TCLIBC TCMODE GIT_PROXY_COMMAND http_proxy ftp_proxy https_proxy all_proxy ALL_PROXY no_proxy SSH_AGENT_PID SSH_AUTH_SOCK BB_SRCREV_POLICY SDKMACHINE BB_NUMBER_THREADS TOPDIR"
export BBPATH="${NIBB_BASE_DIR}:${NIBB_OECORE_DIR}/meta"
EOF
    echo Environment file written to ${NIBB_ENV_FILE}
    cat <<EOF > ${NIBB_BASE_DIR}/conf/site.conf
SCONF_VERSION="1"
DL_DIR="${NIBB_BASE_DIR}/downloads"
SSTATE_DIR="${NIBB_BASE_DIR}/build/sstate-cache"
BBFILES="${NIBB_OECORE_DIR}/meta/recipes-*/*/*.bb"
TMPDIR="${NIBB_BASE_DIR}/build/tmp_${NIBB_DISTDIR}"
#Set the proxy info here
#HTTP_PROXY="http://\${PROXYHOST}:\${PROXYPORT}"
EOF
    cat <<EOF > ${NIBB_BASE_DIR}/conf/auto.conf
export MACHINE="${NIBB_MACHINE}"
EOF
}

if [ $# -gt 0  -a $# -le 2 ]; then
    case $1 in
        update )
            update_source
            exit
            ;;
        config )
            write_config
            exit
            ;;
        info )
            echo I would return info
            ;;
        clean )
            echo I would clean
            ;;
         -h|--help|--usage )
            usage
            ;;
         *)
            echo "Unknown command \"$1\""
            usage
            ;;
    esac
fi

usage

