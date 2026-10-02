"""Tethering forwarding/NAT setup, with subprocess and DBus mocked out."""
from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture

from openpilot.system.ui.lib import wifi_manager
from openpilot.system.ui.lib.wifi_manager import WifiManager


def _fake_run(existing):
  calls = []

  def run(cmd, **_):
    calls.append(cmd)
    if wifi_manager.IPTABLES_LEGACY in cmd:
      return SimpleNamespace(returncode=0 if ('-C' in cmd and existing) or '-A' in cmd else 1, stderr='')
    return SimpleNamespace(returncode=0, stderr='')
  return run, calls


@pytest.mark.parametrize('existing', [False, True])
def test_nat_rules_added_once(mocker: MockerFixture, existing):
  run, calls = _fake_run(existing)
  mocker.patch.object(wifi_manager.os.path, 'exists', return_value=True)
  mocker.patch.object(wifi_manager.subprocess, 'run', side_effect=run)
  WifiManager._ensure_tethering_nat()
  appended = [c for c in calls if '-A' in c]
  if existing:
    assert appended == []
  else:
    assert len(appended) == 3
    assert any('MASQUERADE' in c and '192.168.43.0/24' in c for c in appended)
    assert all(c[:3] == ['sudo', '-n', wifi_manager.IPTABLES_LEGACY] for c in appended)


def test_nat_skipped_without_iptables_legacy(mocker: MockerFixture):
  mocker.patch.object(wifi_manager.os.path, 'exists', return_value=False)
  run = mocker.patch.object(wifi_manager.subprocess, 'run')
  WifiManager._ensure_tethering_nat()
  run.assert_not_called()


@pytest.mark.parametrize('forward', [True, False])
def test_tethering_forwarding_follows_sim_policy(mocker: MockerFixture, forward):
  mocker.patch.object(WifiManager, '_initialize')
  wm = WifiManager.__new__(WifiManager)
  wm._exit = True
  wm._tethering_ssid = 'weedle-test'
  wm._ipv4_forward = forward
  wm.activate_connection = mocker.MagicMock()
  nat = mocker.patch.object(WifiManager, '_ensure_tethering_nat')
  run = mocker.patch.object(wifi_manager.subprocess, 'run')
  mocker.patch.object(wifi_manager.time, 'sleep')
  mocker.patch.object(wifi_manager.threading, 'Thread',
                      side_effect=lambda target, daemon: SimpleNamespace(start=target))
  wm.set_tethering_active(True)
  wm.activate_connection.assert_called_once_with('weedle-test', block=True)
  sysctl = [c.args[0] for c in run.call_args_list if 'sysctl' in c.args[0]]
  assert sysctl == [['sudo', 'sysctl', f'net.ipv4.ip_forward={int(forward)}']]
  assert nat.called == forward
