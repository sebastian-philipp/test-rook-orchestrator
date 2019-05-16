import base64
import time
from subprocess import check_output, CalledProcessError
from typing import List

import requests
import yaml
from kubernetes import client, config
#from kubetest import utils, objects
#from kubetest.client import TestClient
from kubernetes.client import V1Pod, V1Service, V1ServicePort, V1Secret
from pytest import fixture

ceph_image = 'ceph/daemon-base:latest-master'
#ceph_image = '192.168.122.1:5000/ceph/ceph:latest'

def download_rook_manifests():
    def change_flexvolume(text):
        yamls = list(yaml.safe_load_all(text))
        for y in yamls:
            try:
                if y['metadata']['name'] == 'rook-ceph-operator':
                    flex = dict(name='FLEXVOLUME_DIR_PATH', value="/var/lib/kubelet/volumeplugins")
                    y['spec']['template']['spec']['containers'][0]['env'].append(flex)
            except (KeyError, TypeError):
                pass
            try:
                y['spec']['cephVersion']['allowUnsupported'] = True
                y['spec']['cephVersion']['image'] = ceph_image
            except (KeyError, TypeError):
                pass
        return yaml.safe_dump_all(yamls)

    def download(name):
        url = 'https://raw.githubusercontent.com/rook/rook/master/cluster/examples/kubernetes/ceph/{}.yaml'.format(name)
        r = requests.get(url)
        r.raise_for_status()
        with open(name + '.yaml', 'w') as f:
            f.write(change_flexvolume(r.text))

    for name in ['common', 'operator', 'cluster-minimal', 'toolbox', 'dashboard-external-https']:
        download(name)

# @fixture(scope='module')
def rook_operator():
    download_rook_manifests()

    if not get_pods(labels='app=rook-ceph-operator'):
        check_output('./deploy-rook-operator.sh')

    _wait_for_condition(lambda: get_pods(labels='app=rook-ceph-operator'), 240)
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-operator'), 240)
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-agent'), 240)
    _wait_for_condition(lambda: pods_started(labels='app=rook-discover'), 240)

@fixture(scope='module')
def ceph_cluster():
    config.load_kube_config()
    rook_operator()

    check_output('kubectl apply -f cluster-minimal.yaml', shell=True)
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-mon'), 240)
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-mgr'), 240)
    check_output('kubectl apply -f toolbox.yaml', shell=True)  # now depends on running cluster.
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-tools'), 240)
    _wait_for_condition(lambda: _service_exist('mon'))
    _wait_for_condition(lambda: _service_exist('mgr'))
    check_output('kubectl apply -f dashboard-external-https.yaml', shell=True)
    yield None
    check_output('./undeploy-rook-ceph.sh')


def _service_exist(name):
    try:
        return name in _orch_exec('service ls')
    except CalledProcessError:
        return False

def _orch_exec(cmd):
    return _ceph_exec('orchestrator ' + cmd)


def _ceph_exec(cmd):
    return _toolbox_exec('ceph ' + cmd)


def _toolbox_exec(cmd):
    return check_output(f"""timeout 60 kubectl -n rook-ceph exec -it $(kubectl -n rook-ceph get pod -l "app=rook-ceph-tools" -o jsonpath='{{.items[0].metadata.name}}') -- timeout 30 {cmd}""", shell=True).decode('utf-8')


def dashboard_url():
    service: V1Service = client.CoreV1Api().read_namespaced_service('rook-ceph-mgr-dashboard-external-https', 'rook-ceph')
    ports: List[V1ServicePort] = service.spec.ports

    mgr = get_pods(labels='app=rook-ceph-mgr')[0]
    return f'https://{mgr.status.host_ip}:{ports[0].node_port}'


def dashboard_password():
    s: V1Secret = client.CoreV1Api().read_namespaced_secret('rook-ceph-dashboard-password', 'rook-ceph')
    return base64.b64decode(s.data['password']).decode('utf-8')


def dashboard_token_header(url):
    r = requests.post(f'{url}/api/auth', json={'username': 'admin', 'password': dashboard_password()}, verify=False)
    return {'Authorization': f"Bearer {r.json()['token']}"}


def _wait_for_condition(condition, timeout=30):
    max_time = time.time() + timeout

    while True:
        if time.time() >= max_time:
            raise TimeoutError(
                'timed out ({}s) while waiting for condition {}'
                .format(timeout, str(condition))
            )

        if condition():
            break

        time.sleep(1)


def get_pods(namespace='rook-ceph', fields: str=None, labels: str=None) -> List[V1Pod]:
    return client.CoreV1Api().list_namespaced_pod(
        namespace=namespace,
        **_field_labels_kwargs(fields, labels)
    ).items


def _field_labels_kwargs(fields, labels):
    kwargs = {}
    if fields:
        kwargs['field_selector'] = fields
    if labels:
        kwargs['label_selector'] = labels
    return kwargs


def containers_started(p: V1Pod):
    try:
        return all(cs.state.running.started_at is not None for cs in p.status.container_statuses)
    except (AttributeError, TypeError):
        return False


def pods_started(namespace='rook-ceph', fields: str=None, labels: str=None):
    pods = get_pods(namespace, fields=fields, labels=labels)
    if not pods:
        return False
    return all(containers_started(p) for p in pods)


if __name__ == '__main__':
    config.load_kube_config()
    print(dashboard_url())
    print(dashboard_password())

    url = f'{dashboard_url()}/api/summary'
    headers = dashboard_token_header(dashboard_url())#

    requests.get(url, verify=False, headers=headers).raise_for_status()
