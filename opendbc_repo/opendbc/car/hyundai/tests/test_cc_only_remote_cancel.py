from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker
from opendbc.car.hyundai.carcontroller import CC_ONLY_PRESS_FRAMES, CC_ONLY_RESUME_LOCKOUT_FRAMES, CarController, CcOnlyRemoteButtons
from opendbc.car.hyundai.values import Buttons, HyundaiFlags, REMOTE_CANCEL_REQUEST, REMOTE_CRUISE_TOGGLE_REQUEST
from openpilot.selfdrive.carrot.bluetooth.model import BLUETOOTH_CANCEL, BLUETOOTH_CRUISE_TOGGLE

CLU11_SIGNALS = ("CF_Clu_CruiseSwState", "CF_Clu_CruiseSwMain", "CF_Clu_SldMainSW", "CF_Clu_ParityBit1", "CF_Clu_VanzDecimal",
                 "CF_Clu_Vanz", "CF_Clu_SPEED_UNIT", "CF_Clu_DetentOut", "CF_Clu_RheostatLevel", "CF_Clu_CluInfo", "CF_Clu_AmpInfo",
                 "CF_Clu_AliveCnt1")
NONE, RES, CANCEL = Buttons.NONE, Buttons.RES_ACCEL, Buttons.CANCEL


def test_requests_match_bluetooth_actions():
  assert (REMOTE_CANCEL_REQUEST, REMOTE_CRUISE_TOGGLE_REQUEST) == (BLUETOOTH_CANCEL, BLUETOOTH_CRUISE_TOGGLE)


def _press(buttons, request, lamp_on, frames):
  return [buttons.update(request if i == 0 else 0, lamp_on) for i in range(frames)]


@pytest.mark.parametrize("request_value", [REMOTE_CANCEL_REQUEST, REMOTE_CRUISE_TOGGLE_REQUEST])
def test_engaged_press_is_one_cancel_window(request_value):
  assert _press(CcOnlyRemoteButtons(), request_value, True, CC_ONLY_PRESS_FRAMES + 20) == [CANCEL] * CC_ONLY_PRESS_FRAMES + [NONE] * 20


def test_cancel_request_is_ignored_while_cruise_is_off():
  assert _press(CcOnlyRemoteButtons(), REMOTE_CANCEL_REQUEST, False, 10) == [NONE] * 10


def test_toggle_resumes_when_cruise_has_been_off():
  assert _press(CcOnlyRemoteButtons(), REMOTE_CRUISE_TOGGLE_REQUEST, False, CC_ONLY_PRESS_FRAMES + 20) == \
         [RES] * CC_ONLY_PRESS_FRAMES + [NONE] * 20


@pytest.mark.parametrize("button, lamp_before, lamp_after", [(CANCEL, True, False), (RES, False, True)])
def test_press_stops_as_soon_as_the_lamp_shows_the_effect(button, lamp_before, lamp_after):
  buttons = CcOnlyRemoteButtons()
  request = REMOTE_CANCEL_REQUEST if button == CANCEL else REMOTE_CRUISE_TOGGLE_REQUEST
  assert buttons.update(request, lamp_before) == button
  assert buttons.update(0, lamp_before) == button
  assert buttons.update(0, lamp_after) == NONE
  assert buttons.update(0, lamp_before) == NONE


def test_resume_locked_out_after_cruise_turns_off():
  buttons = CcOnlyRemoteButtons()
  buttons.update(0, True)  # cruise engaged, e.g. just cancelled from the wheel
  for _ in range(CC_ONLY_RESUME_LOCKOUT_FRAMES - 2):
    assert buttons.update(0, False) == NONE
  assert buttons.update(REMOTE_CRUISE_TOGGLE_REQUEST, False) == NONE  # lamp off for 1.99 s
  assert buttons.update(REMOTE_CRUISE_TOGGLE_REQUEST, False) == RES  # lamp off for 2.00 s


def test_second_toggle_right_after_a_remote_cancel_never_resumes():
  buttons = CcOnlyRemoteButtons()
  assert buttons.update(REMOTE_CRUISE_TOGGLE_REQUEST, True) == CANCEL
  assert buttons.update(0, False) == NONE  # cancel took effect
  assert _press(buttons, REMOTE_CRUISE_TOGGLE_REQUEST, False, 20) == [NONE] * 20


def test_brake_aborts_a_resume_and_restarts_the_lockout():
  buttons = CcOnlyRemoteButtons()
  assert buttons.update(REMOTE_CRUISE_TOGGLE_REQUEST, False) == RES
  buttons.abort()
  assert buttons.update(0, False) == NONE
  assert buttons.update(REMOTE_CRUISE_TOGGLE_REQUEST, False) == NONE


@pytest.mark.parametrize("request_value", [-2, -1, 0, 1])
def test_other_requests_never_press(request_value):
  buttons = CcOnlyRemoteButtons()
  assert buttons.update(request_value, True) == NONE
  assert buttons.update(request_value, False) == NONE


def _button_messages(cc_only, activate_cruise, lamp_on, brake=False):
  packer = CANPacker("hyundai_kia_generic")
  spam_calls = []
  controller = SimpleNamespace(
    CP=SimpleNamespace(flags=HyundaiFlags.CC_ONLY_CAR.value if cc_only else 0),
    cc_only_remote_buttons=CcOnlyRemoteButtons(), packer=packer, frame=10, last_button_frame=0,
    make_spam_button=lambda CC, CS: spam_calls.append(1) or 0,
  )
  CS = SimpleNamespace(clu11=dict.fromkeys(CLU11_SIGNALS, 0),
                       out=SimpleNamespace(brakePressed=brake, brakeHoldActive=False, parkingBrake=False,
                                           activateCruise=activate_cruise, cruiseLampOn=lamp_on))
  CC = SimpleNamespace(cruiseControl=SimpleNamespace(cancel=False, resume=False))
  sends = CarController.create_button_messages(controller, CC, CS, use_clu11=True)
  return sends, spam_calls


@pytest.mark.parametrize("request_value, lamp_on, button", [
  (REMOTE_CANCEL_REQUEST, True, CANCEL),
  (REMOTE_CRUISE_TOGGLE_REQUEST, True, CANCEL),
  (REMOTE_CRUISE_TOGGLE_REQUEST, False, RES),
])
def test_cc_only_remote_sends_one_clu11_button(request_value, lamp_on, button):
  sends, spam_calls = _button_messages(cc_only=True, activate_cruise=request_value, lamp_on=lamp_on)
  assert len(sends) == 1
  addr, dat, bus = sends[0]
  # panda reads the CLU11 button from the low 3 bits of byte 0
  assert (addr, bus, dat[0] & 0x7) == (0x4F1, 0, button)
  assert spam_calls == []


@pytest.mark.parametrize("request_value", [REMOTE_CANCEL_REQUEST, REMOTE_CRUISE_TOGGLE_REQUEST])
@pytest.mark.parametrize("kwargs", [{"cc_only": False, "lamp_on": True}, {"cc_only": False, "lamp_on": False},
                                    {"cc_only": True, "lamp_on": True, "brake": True},
                                    {"cc_only": True, "lamp_on": False, "brake": True}])
def test_no_remote_button_without_cc_only_or_while_braking(request_value, kwargs):
  sends, _ = _button_messages(activate_cruise=request_value, **kwargs)
  assert sends == []
