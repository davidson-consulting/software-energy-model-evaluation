echo 0 > /sys/fs/cgroup/cpuset/$1_c$2/cpuset.mems
echo $2 > /sys/fs/cgroup/cpuset/$1_c$2/cpuset.cpus
