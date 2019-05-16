#!/usr/bin/env bash
set -x

crs="CephNFS CephObjectStore CephFilesystem CephCluster job"
apps="mon mgr osd mds rgw tools"

# finalizers can deadlock
timeout 30 kubectl patch --namespace=rook-ceph deployment rook-ceph-operator -p '{"spec": {"replicas": 0}}'
timeout 30 kubectl patch --namespace=rook-ceph crd cephcluster.ceph.rook.io -p '{"metadata":{"finalizers":[]}}' --type=merge
timeout 30 kubectl patch --namespace=rook-ceph cephcluster.ceph.rook.io rook-ceph -p '{"metadata":{"finalizers":[]}}' --type=merge

for cr in $crs
do
    timeout 30 kubectl delete --namespace=rook-ceph $cr --grace-period=0 --force --all
done

timeout 30 kubectl delete -f cluster-minimal.yaml
timeout 30 kubectl delete -f toolbox.yaml
timeout 30 kubectl delete --namespace=rook-ceph pod -n rook-ceph -l app=rook-ceph-operator

for primitive in service deployment pod
do
    for app in $(echo $apps)
    do
        timeout 30 kubectl delete --namespace=rook-ceph $primitive --grace-period=0 --force -l app=rook-ceph-$app
    done
done

timeout 30 kubectl delete pod --namespace=rook-ceph -l job=rook-ceph-detect-version
timeout 30 kubectl delete pod --namespace=rook-ceph -l job-name=rook-ceph-nfs-ganesha-rados-grace

for app in $(echo $apps)
do
    while kubectl get pod --namespace=rook-ceph -l app=rook-ceph-$app -o json | jq -e '.items[0].metadata.labels.app' ; do
        sleep 1
    done
done

for cr in $(echo $crs)
do
    while kubectl get --namespace=rook-ceph $cr rook-ceph ; do
        sleep 1
    done
done


pushd ./kubic-terraform-kvm
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

kubectl patch --namespace=rook-ceph deployment rook-ceph-operator  -p '{"spec": {"replicas": 1}}'


