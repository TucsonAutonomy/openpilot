"""APN/CID selection in the PPP modem manager, with the AT channel and pppd mocked out."""
import pytest
from pytest_mock import MockerFixture

from openpilot.system.hardware.tici import modem


def _init(mocker: MockerFixture, apn: str):
  m = modem.Modem()
  sent = []
  mocker.patch.object(modem.os.path, 'exists', return_value=True)
  mocker.patch.object(modem.PPPSession, 'kill')
  mocker.patch.object(modem.PPPSession, 'cleanup_routes')
  mocker.patch.object(m, '_init_at_channel', return_value=True)
  mocker.patch.object(m, '_read_identity', return_value={'imei': '1', 'iccid': '2', 'mcc_mnc': '45008',
                                                         'modem_version': 'EG25', 'sim_state': 'READY'})
  mocker.patch.object(m, '_configure_modem')
  mocker.patch.object(m, '_publish_state')
  mocker.patch.object(m, '_read_param', side_effect=lambda key: apn if key == 'GsmApn' else '')
  mocker.patch.object(m, '_at', side_effect=lambda cmd, **_: sent.append(cmd) or [])
  assert m._do_initializing() == modem.State.SEARCHING
  return m, [c for c in sent if c.startswith('AT+CGDCONT')]


def test_configured_apn_dials_its_own_cid(mocker: MockerFixture):
  m, cgdcont = _init(mocker, 'lte.ktfwing.com')
  # the attach context never carries the dialed APN, so a reboot cannot make them equal
  assert cgdcont == ['AT+CGDCONT=1,"IP",""', 'AT+CGDCONT=2,"IP","lte.ktfwing.com"']
  assert m._ppp.cid == modem.APN_DIAL_CID


def test_blank_apn_keeps_attach_cid(mocker: MockerFixture):
  m, cgdcont = _init(mocker, '')
  assert cgdcont == ['AT+CGDCONT=1,"IP",""']
  assert m._ppp.cid == modem.ATTACH_CID


@pytest.mark.parametrize('cid', [1, 2])
def test_pppd_dials_selected_cid(mocker: MockerFixture, cid):
  popen = mocker.patch.object(modem.subprocess, 'Popen')
  ppp = modem.PPPSession()
  ppp.cid = cid
  ppp.start()
  chat = next(arg for arg in popen.call_args.args[0] if 'chat' in arg)
  assert f"ATD*99***{cid}#" in chat


def test_dns_reads_dialed_cid(mocker: MockerFixture):
  m = modem.Modem()
  m._ppp.cid = 2
  atv = mocker.patch.object(m, '_atv', return_value='2,5,"lte.ktfwing.com","10.0.0.2","10.64.64.64","211.219.86.1","39.16.0.1"')
  assert m._read_cellular_dns() == ['211.219.86.1', '39.16.0.1']
  atv.assert_called_once_with("AT+CGCONTRDP=2", "+CGCONTRDP:")
