#!/usr/bin/env bash


. config_paths.sh

kubectl apply -f $rook_path/common.yaml
kubectl apply -f $rook_path/operator.yaml