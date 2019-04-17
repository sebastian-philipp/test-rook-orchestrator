#!/usr/bin/env bash

set -e

pushd ./kubic-terraform-kvm

terraform destroy -auto-approve

popd