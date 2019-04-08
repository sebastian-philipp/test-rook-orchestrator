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
    _wait_for_condition(_has_tools_pod, 120)
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
    """Get Pods from the cluster.

    Args:
        namespace (str): The namespace to get the Pods from. If not
            specified, it will use the auto-generated test case namespace
            by default.
        fields (dict[str, str]): A dictionary of fields used to restrict
            the returned collection of Pods to only those which match
            these field selectors. By default, no restricting is done.
        labels (dict[str, str]): A dictionary of labels used to restrict
            the returned collection of Pods to only those which match
            these label selectors. By default, no restricting is done.

    Returns:
        dict[str, objects.Pod]: A dictionary where the key is the Pod
        name and the value is the Pod itself.
    """
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
    containers_started = True

    status = p.status # type: V1PodStatus
    if status:
        for container_status in status.container_statuses:
            if container_status.state is not None:
                if container_status.state.running is not None:
                    if container_status.state.running.started_at is not None:
                        # The container is started, so move on to check the
                        # next container
                        continue
            # If we get here, then the container has not started.
            containers_started = containers_started and False
            break

    return containers_started
