#!/bin/sh
set -e

error_and_die () {
    echo >&2 "ERROR: $1"
    exit 1
}

print_usage_and_die () {
    echo >&2 "Usage: $0 -h | -r <recipe name of an initramfs for the ISO to boot>"
    echo >&2 ' Must be run from a bitbake environment.'
    echo >&2 ' MACHINE env must be defined.'
    exit 1
}

# get args
initramfsRecipeName=''

while getopts "r:h" opt; do
   case "$opt" in
   r )  initramfsRecipeName="$OPTARG" ;;
   h )  print_usage_and_die ;;
   \?)  print_usage_and_die ;;
   esac
done
shift $(($OPTIND - 1))

[ -n "$initramfsRecipeName" ] || error_and_die 'Must specify recipe name with -r. Run with -h for help.'

# check env
[ -n "$MACHINE" ] || error_and_die 'No MACHINE specified in env'
bitbake --parse-only >/dev/null || error_and_die 'Bitbake failed. Check your environment. This script must be run from the build directory.'

wicOutputDir='./wic-temp-output-dir'
isoDstDir="./tmp-glibc/deploy/images/$MACHINE"

# make output build dir
[ ! -e "$wicOutputDir" ] || rm -R "$wicOutputDir"
mkdir "$wicOutputDir"

# wic away
wic create mk-NI-hybridiso -e "$initramfsRecipeName" -o "$wicOutputDir"
echo ''

# save the ISO
mkdir -p "$isoDstDir"
isoDst="$isoDstDir/$initramfsRecipeName-$MACHINE.iso"
mv "$wicOutputDir/NI_RECOVERY_IMG-cd.iso" "$isoDst"
echo "Saved ISO to $isoDst"
