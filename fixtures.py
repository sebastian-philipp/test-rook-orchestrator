import time
from subprocess import check_output, CalledProcessError
from typing import List

from kubernetes import client, config
#from kubetest import utils, objects
#from kubetest.client import TestClient
from kubernetes.client import V1Pod, V1PodStatus
from pytest import fixture


@fixture(scope='module')
def ceph_cluster():

    check_output('./deploy-rook-ceph.sh')
    _wait_for_condition(_has_tools_pod, 240)
    _wait_for_condition(lambda: _service_exist('mon'))
    _wait_for_condition(lambda: _service_exist('mgr'))
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


def _has_tools_pod():
    ps = get_pods(labels='app=rook-ceph-tools')
    if not ps:
        return False
    p = list(ps)[0]
    return containers_started(p)


def get_pods(namespace='rook-ceph', fields: str=None, labels: str=None) -> List[V1Pod]:
    config.load_kube_config()

    kwargs = {}
    if fields:
        kwargs['field_selector'] = fields
    if labels:
        kwargs['label_selector'] = labels

    pod_list = client.CoreV1Api().list_namespaced_pod(
        namespace=namespace,
        **kwargs
    )

    return pod_list.items


def containers_started(p: V1Pod):
    try:
        return all(cs.state.running.started_at is not None for cs in p.status.container_statuses)
    except (AttributeError, TypeError):
        return False


def pods_started(namespace='rook-ceph', fields: str=None, labels: str=None):
    pods = get_pods(namespace, fields=fields, labels=labels)
    return all(containers_started(p) for p in pods)
