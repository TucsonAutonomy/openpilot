from types import SimpleNamespace

from opendbc.can import CANPacker
from opendbc.car.hyundai.carcontroller import CC_ONLY_CANCEL_FRAMES, CarController, CcOnlyRemoteCancel
from opendbc.car.hyundai.values import Buttons, HyundaiFlags, REMOTE_CANCEL_REQUEST
from openpilot.selfdrive.carrot.bluetooth.model import BLUETOOTH_CANCEL

CLU11_SIGNALS = ("CF_Clu_CruiseSwState", "CF_Clu_CruiseSwMain", "CF_Clu_SldMainSW", "CF_Clu_ParityBit1", "CF_Clu_VanzDecimal",
                 "CF_Clu_Vanz", "CF_Clu_SPEED_UNIT", "CF_Clu_DetentOut", "CF_Clu_RheostatLevel", "CF_Clu_CluInfo", "CF_Clu_AmpInfo",
                 "CF_Clu_AliveCnt1")


def test_request_matches_bluetooth_cancel():
  assert REMOTE_CANCEL_REQUEST == BLUETOOTH_CANCEL


def test_presses_cancel_for_one_window_while_lamp_on():
  cancel = CcOnlyRemoteCancel()
  pressed = [cancel.update(REMOTE_CANCEL_REQUEST if i == 0 else 0, True) for i in range(CC_ONLY_CANCEL_FRAMES + 20)]
  assert pressed == [True] * CC_ONLY_CANCEL_FRAMES + [False] * 20


def test_ignored_when_factory_cruise_off():
  cancel = CcOnlyRemoteCancel()
  assert not cancel.update(REMOTE_CANCEL_REQUEST, False)
  assert not any(cancel.update(0, False) for _ in range(5))


def test_stops_as_soon_as_cruise_lamp_goes_off():
  cancel = CcOnlyRemoteCancel()
  assert cancel.update(REMOTE_CANCEL_REQUEST, True)
  assert cancel.update(0, True)
  assert not cancel.update(0, False)
  assert not cancel.update(0, True)


def test_other_activate_values_never_press():
  cancel = CcOnlyRemoteCancel()
  assert not any(cancel.update(value, True) for value in (-2, -1, 0, 1))


def _button_messages(cc_only, activate_cruise, lamp_on, brake=False):
  packer = CANPacker("hyundai_kia_generic")
  spam_calls = []
  controller = SimpleNamespace(
    CP=SimpleNamespace(flags=HyundaiFlags.CC_ONLY_CAR.value if cc_only else 0),
    cc_only_remote_cancel=CcOnlyRemoteCancel(), packer=packer, frame=10, last_button_frame=0,
    make_spam_button=lambda CC, CS: spam_calls.append(1) or 0,
  )
  CS = SimpleNamespace(clu11=dict.fromkeys(CLU11_SIGNALS, 0),
                       out=SimpleNamespace(brakePressed=brake, brakeHoldActive=False, parkingBrake=False,
                                           activateCruise=activate_cruise, cruiseLampOn=lamp_on))
  CC = SimpleNamespace(cruiseControl=SimpleNamespace(cancel=False, resume=False))
  sends = CarController.create_button_messages(controller, CC, CS, use_clu11=True)
  return sends, spam_calls


def test_cc_only_remote_cancel_sends_clu11_cancel():
  sends, spam_calls = _button_messages(cc_only=True, activate_cruise=REMOTE_CANCEL_REQUEST, lamp_on=True)
  assert len(sends) == 1
  addr, dat, bus = sends[0]
  # panda reads the CLU11 button from the low 3 bits of byte 0
  assert (addr, bus, dat[0] & 0x7) == (0x4F1, 0, Buttons.CANCEL)
  assert spam_calls == []


def test_no_cancel_without_cc_only_or_lamp_or_while_braking():
  for kwargs in ({"cc_only": False, "lamp_on": True}, {"cc_only": True, "lamp_on": False},
                 {"cc_only": True, "lamp_on": True, "brake": True}):
    sends, _ = _button_messages(activate_cruise=REMOTE_CANCEL_REQUEST, **kwargs)
    assert sends == []
