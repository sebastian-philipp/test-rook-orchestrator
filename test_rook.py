import json

import pytest

from fixtures import _orch_exec, _wait_for_condition, _service_exist, _ceph_exec, ceph_cluster, \
    get_pods, pods_started


def test_status(ceph_cluster):
    _orch_exec('status')

def test_service_ls(ceph_cluster):
    svs = json.loads(_orch_exec('service ls --format=json'))
    assert len(svs) >= 2


def test_device_ls(ceph_cluster):
    svs = json.loads(_orch_exec('device ls --format=json'))
    assert len(svs) >= 2


def test_mon_update(ceph_cluster):
    assert len(get_pods(labels='app=rook-ceph-mon')) < 3
    _orch_exec('mon update 3')
    _wait_for_condition(lambda: len(get_pods(labels='app=rook-ceph-mon')) == 3)


def test_osd_create(ceph_cluster):
    assert 'osd' not in  _orch_exec('service ls')
    _orch_exec('osd create kubic-1:vdb')
    _orch_exec('osd create kubic-2:vdb')
    _wait_for_condition(lambda: len(get_pods(labels='app=rook-ceph-osd')) >= 1, timeout=120)
    _wait_for_condition(lambda: len(get_pods(labels='app=rook-ceph-osd')) == 2, timeout=120)
    _wait_for_condition(lambda:  _service_exist('osd'))
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-osd'))


@pytest.mark.skip(reason="needs image rebuild")
def test_nfs(ceph_cluster):
    assert _service_exist('osd')
    if not 'nfs-ganesha' in _ceph_exec('osd pool ls'):
        _ceph_exec("osd pool create nfs-ganesha 64")
    assert not _service_exist('nfs')

    _orch_exec("nfs add mynfs nfs-ganesha mynfs")
    _wait_for_condition(lambda: len(get_pods(labels='app=rook-ceph-nfs')) >= 1, timeout=120)
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-nfs'), timeout=60)
    _wait_for_condition(lambda: _service_exist('nfs'))


def test_mds(ceph_cluster):
    assert not _service_exist('mds')
    _ceph_exec('fs volume create myname')
    _wait_for_condition(lambda: len(get_pods(labels='app=rook-ceph-mds')) == 2)
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-mds'))
    _wait_for_condition(lambda: _service_exist('mds'))

    _ceph_exec('fs volume rm myname')
    _wait_for_condition(lambda: not _service_exist('mds'))
    _wait_for_condition(lambda: not get_pods(labels='app=rook-ceph-mds'))


@pytest.mark.skip(reason="needs image rebuild")
def test_rgw(ceph_cluster):
    assert not _service_exist('rgw')
    _orch_exec("rgw add myrgw")
    _wait_for_condition(lambda: len(get_pods(labels='app=rook-ceph-rgw')) >= 1)
    _wait_for_condition(lambda: pods_started(labels='app=rook-ceph-rgw'))
    _wait_for_condition(lambda: _service_exist('rgw'))
