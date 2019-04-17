#!/usr/bin/env bash

set -e

which kubectl > /dev/null
which terraform > /dev/null

if [ "$(kubectl get nodes | grep ' Ready ' | wc -l)" == 3 ]
then
    echo -e "\e[91mWARNING: re-using exiting Kubernetes cluster.\e[39m"
    exit
fi

pushd ./kubic-terraform-kvm

timeout 3m ./download-image.sh
terraform init
terraform plan
terraform apply -auto-approve
./mk-ssh-config.sh


cat <<'EOF' | ssh -F ssh_config $(terraform output -json | jq -r '.ips.value[0][]') 'bash -s'
kubeadm init --cri-socket=/var/run/crio/crio.sock --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
EOF


join_command=$(ssh -F ssh_config $(terraform output -json | jq -r '.ips.value[0][]') "kubeadm token create --print-join-command")
join_command="kubeadm join --cri-socket=/var/run/crio/crio.sock $(echo $join_command | python -c 'import sys; print(" ".join(sys.stdin.read().split()[2:]))')"
ssh -F ssh_config $(terraform output -json | jq -r '.ips.value[1][]') "$join_command"
ssh -F ssh_config $(terraform output -json | jq -r '.ips.value[2][]') "$join_command"


scp -F ssh_config $(terraform output -json | jq -r '.ips.value[0][]'):~/.kube/config ~/.kube/config


timeout 5m bash <<EOF
while [ "$(kubectl get nodes | grep ' Ready ' | wc -l)" != 3 ]
do
  sleep 1
done
EOF


popd