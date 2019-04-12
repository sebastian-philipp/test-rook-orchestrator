#!/usr/bin/env bash
set -x

. config_paths.sh

crs="CephNFS CephObjectStore CephFilesystem CephCluster"
apps="mon mgr osd mds rgw tools"

for cr in $crs
do
    timeout 30 kubectl delete $cr --all
done

timeout 30 kubectl delete -f $rook_path/cluster.yaml
timeout 30 kubectl delete -f $rook_path/toolbox.yaml
timeout 30 kubectl delete pod -n rook-ceph-system -l app=rook-ceph-operator

for cr in $(echo $crs)
do
    while kubectl get $cr rook-ceph ; do
        sleep 1
    done
done

for primitive in service deployment pod
do
    for app in $(echo $apps)
    do
        timeout 30 kubectl delete $primitive -l app=rook-ceph-$app
    done
done

for app in $(echo $apps)
do
    while kubectl get pod -l app=rook-ceph-$app -o json | jq -e '.items[0].metadata.labels.app' ; do
        sleep 1
    done
done


pushd $kubic_path
for h in $(terraform output -json | jq -r '.ips.value[][]')
do
    cat <<'EOF' | ssh -F ssh_config $h 'bash -x -s'
#!/usr/bin/env bash
# Zap the disk to a fresh, usable state (zap-all is important, b/c MBR has to be clean)
# You will have to run this step for all disks.
sgdisk --zap-all /dev/vdb

# These steps only have to be run once on each node
# If rook sets up osds using ceph-volume, teardown leaves some devices mapped that lock the disks.
ls /dev/mapper/ceph-* | xargs -I% -- dmsetup remove %
# ceph-volume setup can leave ceph-<UUID> directories in /dev (unnecessary clutter)
rm -rf /dev/ceph-*
rm -rf /var/lib/rook
EOF
done
popd


