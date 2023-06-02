#!/usr/bin/env sh

sudo cgexec -g cpu:custom.slice/test ./stress-ng.exe -c ${2} --cpu-method ${1} --cpu-ops ${3}
