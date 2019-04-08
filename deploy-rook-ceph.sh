#!/usr/bin/env bash
set -x


. config_paths.sh

kubectl apply -f $rook_path/cluster-minimal.yaml
kubectl apply -f $rook_path/toolbox.yaml
