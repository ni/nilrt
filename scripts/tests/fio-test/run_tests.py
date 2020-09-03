#!/bin/bash
opkg update
opkg install fio

for i in *.fio; do
    echo =========$i========= &>> fio.output;
    fio $i &>> fio.output;
done
