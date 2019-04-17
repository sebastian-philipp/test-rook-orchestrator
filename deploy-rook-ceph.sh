#!/usr/bin/env bash
set -ex

kubectl apply -f cluster-minimal.yaml
kubectl apply -f toolbox.yaml
