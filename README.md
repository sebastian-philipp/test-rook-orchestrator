# Test Ceph Rook Orchestrator 

py.test project to run an integration test of Ceph's mgr/rook module.

## Requirements

* from: [`kubic-terraform-kvm`](https://github.com/kubic-project/kubic-terraform-kvm)
    * `terraform`
    * [`terraform-provider-libvirt`](https://github.com/dmacvicar/terraform-provider-libvirt)
* docker
* kubectl
* ssh
    
## Configuration

This test deploys the minimal cluster.

  
## Usage

Simple, just run:
```bash
tox
```