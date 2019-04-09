# Test Ceph Rook Orchestrator 

py.test project to run an integration test of Ceph's mgr/rook module.

## Requirements

* https://github.com/kubic-project/kubic-terraform-kvm
* and
    ```bash
    kubectl config set-context rook-ceph-namespace --namespace=rook-ceph --user=kubernetes-admin --cluster=kubernetes
    kubectl config use-context rook-ceph-namespace
    ```
    (TODO: remove ^^^)
    
## Configuration

* Create a `config_paths.sh` containing bash vars for `rook_path` and `kubic_path`. e.g.:
    ```bash
    cat <<EOF > config_paths.sh
    rook_path=$HOME/go/src/github.com/rook/rook/cluster/examples/kubernetes/ceph
    kubic_path=$HOME/kubic-terraform-kvm
    EOF
    ``` 

This test deploys the minimal cluster. Make sure, it points to the correct image. 
  
## Usage

Simple, just run:
```bash
pytest
```