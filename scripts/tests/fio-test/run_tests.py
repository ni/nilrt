#!/bin/bash
which fio &> /dev/null || (opkg update; opkg install fio; sleep 5;)

hn=`hostname`
un=`uname -r`
dt=`date "+%F-%T"`
fn="$hn"__"$un"__"$dt".output

for i in *.fio; do
    echo =========$i========= &>> $fn;
    fio $i &>> $fn;
    sleep 5;
done
