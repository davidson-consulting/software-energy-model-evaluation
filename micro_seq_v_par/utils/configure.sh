#!/usr/bin/env sh

apt install -y cgroup-tools libpfm4-dev stress libssl-dev
dpkg -i ./anon.deb

wget https://github.com/hubblo-org/scaphandre/releases/download/v0.5.0/scaphandre_linux_amd64 -O scaphandre
mv scaphandre /usr/bin/scaphandre
chmod +x /usr/bin/scaphandre

cp stress-ng.exe /usr/bin/
chmod +x /usr/bin/stress-ng.exe
