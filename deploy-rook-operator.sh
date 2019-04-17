#!/usr/bin/env bash

set -ex

kubectl apply -f common.yaml
kubectl apply -f operator.yaml