from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker
from opendbc.car.hyundai.carcontroller import CC_ONLY_ENGAGE_LOCKOUT_FRAMES, CC_ONLY_PRESS_FRAMES, CC_ONLY_SET_PRESS_FRAMES, \
                                              CC_ONLY_SET_WATCH_FRAMES, CC_ONLY_STEP_FRAMES, CarController, CcOnlyRemoteButtons
from opendbc.car.hyundai.values import Buttons, HyundaiFlags, REMOTE_CANCEL_REQUEST, REMOTE_CRUISE_RES_ACCEL_REQUEST, \
                                       REMOTE_CRUISE_SET_DECEL_REQUEST, REMOTE_CRUISE_SET_REQUEST, REMOTE_CRUISE_TOGGLE_REQUEST
from openpilot.selfdrive.carrot.bluetooth.model import BLUETOOTH_CANCEL, BLUETOOTH_CRUISE_RES_ACCEL, BLUETOOTH_CRUISE_SET, \
                                                       BLUETOOTH_CRUISE_SET_DECEL, BLUETOOTH_CRUISE_TOGGLE

CLU11_SIGNALS = ("CF_Clu_CruiseSwState", "CF_Clu_CruiseSwMain", "CF_Clu_SldMainSW", "CF_Clu_ParityBit1", "CF_Clu_VanzDecimal",
                 "CF_Clu_Vanz", "CF_Clu_SPEED_UNIT", "CF_Clu_DetentOut", "CF_Clu_RheostatLevel", "CF_Clu_CluInfo", "CF_Clu_AmpInfo",
                 "CF_Clu_AliveCnt1")
NONE, RES, SET, CANCEL = Buttons.NONE, Buttons.RES_ACCEL, Buttons.SET_DECEL, Buttons.CANCEL
WHEEL = [(REMOTE_CRUISE_RES_ACCEL_REQUEST, RES), (REMOTE_CRUISE_SET_DECEL_REQUEST, SET)]


def test_requests_match_bluetooth_actions():
  assert (REMOTE_CANCEL_REQUEST, REMOTE_CRUISE_TOGGLE_REQUEST, REMOTE_CRUISE_SET_REQUEST,
          REMOTE_CRUISE_RES_ACCEL_REQUEST, REMOTE_CRUISE_SET_DECEL_REQUEST) == \
         (BLUETOOTH_CANCEL, BLUETOOTH_CRUISE_TOGGLE, BLUETOOTH_CRUISE_SET, BLUETOOTH_CRUISE_RES_ACCEL, BLUETOOTH_CRUISE_SET_DECEL)


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
  for _ in range(CC_ONLY_ENGAGE_LOCKOUT_FRAMES - 2):
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


def test_set_engages_at_current_speed_when_cruise_has_been_off():
  # longer than CANCEL/RES: the factory cruise is slower to take SET, above all with the accelerator pressed
  assert _press(CcOnlyRemoteButtons(), REMOTE_CRUISE_SET_REQUEST, False, CC_ONLY_SET_PRESS_FRAMES + 20) == \
         [SET] * CC_ONLY_SET_PRESS_FRAMES + [NONE] * 20


def test_set_press_logs_how_long_the_lamp_took(capsys):
  buttons = CcOnlyRemoteButtons()
  assert _press(buttons, REMOTE_CRUISE_SET_REQUEST, False, 45) == [SET] * 45
  assert buttons.update(0, True) == NONE
  assert "factory cruise on after 45 frames of SET" in capsys.readouterr().out


@pytest.mark.parametrize("lamp_frame, expected", [(120, "factory cruise on 1.20s after the SET press ended"),
                                                  (None, "factory cruise still off 3.00s after the SET press ended")])
def test_lamp_is_watched_after_a_set_press_without_effect(capsys, lamp_frame, expected):
  buttons = CcOnlyRemoteButtons()
  _press(buttons, REMOTE_CRUISE_SET_REQUEST, False, CC_ONLY_SET_PRESS_FRAMES)
  for frame in range(1, CC_ONLY_SET_WATCH_FRAMES + 50):
    assert buttons.update(0, lamp_frame is not None and frame >= lamp_frame) == NONE
  out = capsys.readouterr().out
  assert "SET window ended with factory cruise still off" in out
  assert out.count("after the SET press ended") == 1
  assert expected in out


@pytest.mark.parametrize("interrupt, ended", [("brake", "0.50s after the SET press ended (brake)"),
                                              ("press", "0.51s after the SET press ended (new remote press)")])  # counts the press frame
def test_set_watch_ends_on_brake_or_a_new_press(capsys, interrupt, ended):
  buttons = CcOnlyRemoteButtons()
  _press(buttons, REMOTE_CRUISE_SET_REQUEST, False, CC_ONLY_SET_PRESS_FRAMES)
  for _ in range(50):
    buttons.update(0, False)
  if interrupt == "brake":
    buttons.abort()
  else:
    assert buttons.update(REMOTE_CRUISE_SET_REQUEST, False) == SET
  for _ in range(CC_ONLY_SET_WATCH_FRAMES):
    buttons.update(0, True)  # a later engagement no longer belongs to the first press
  out = capsys.readouterr().out
  assert f"factory cruise still off {ended}" in out
  assert out.count("after the SET press ended") == 1


@pytest.mark.parametrize("request_value, lamp_on", [(REMOTE_CRUISE_TOGGLE_REQUEST, False), (REMOTE_CRUISE_TOGGLE_REQUEST, True)])
def test_cancel_and_res_presses_are_not_watched(capsys, request_value, lamp_on):
  _press(CcOnlyRemoteButtons(), request_value, lamp_on, CC_ONLY_PRESS_FRAMES + CC_ONLY_SET_WATCH_FRAMES)
  out = capsys.readouterr().out
  assert "window ended" in out and "after the SET press ended" not in out


def test_set_does_nothing_while_cruise_is_engaged():
  # The wheel SET would lower the set speed here; the remote set only starts cruise.
  assert _press(CcOnlyRemoteButtons(), REMOTE_CRUISE_SET_REQUEST, True, 20) == [NONE] * 20


def test_set_stops_as_soon_as_cruise_engages():
  buttons = CcOnlyRemoteButtons()
  assert buttons.update(REMOTE_CRUISE_SET_REQUEST, False) == SET
  assert buttons.update(0, False) == SET
  assert buttons.update(0, True) == NONE
  assert buttons.update(0, False) == NONE


@pytest.mark.parametrize("request_value, button", [(REMOTE_CRUISE_SET_REQUEST, SET), (REMOTE_CRUISE_TOGGLE_REQUEST, RES), *WHEEL])
def test_engage_requests_share_the_lockout_and_brake_abort(request_value, button):
  buttons = CcOnlyRemoteButtons()
  buttons.update(0, True)
  assert buttons.update(request_value, False) == NONE  # cruise just turned off
  for _ in range(CC_ONLY_ENGAGE_LOCKOUT_FRAMES):
    buttons.update(0, False)
  assert buttons.update(request_value, False) == button
  buttons.abort()
  assert buttons.update(0, False) == NONE
  assert buttons.update(request_value, False) == NONE


@pytest.mark.parametrize("request_value, button", WHEEL)
def test_wheel_request_is_one_speed_step_while_engaged(capsys, request_value, button):
  # no lockout: cruise has just come on, and the lamp staying on does not end the tap early
  buttons = CcOnlyRemoteButtons()
  buttons.update(0, True)
  assert _press(buttons, request_value, True, CC_ONLY_STEP_FRAMES + 20) == [button] * CC_ONLY_STEP_FRAMES + [NONE] * 20
  out = capsys.readouterr().out
  name = "RES" if button == RES else "SET"
  assert f"sending CLU11 {name} step" in out and f"{name} step sent for {CC_ONLY_STEP_FRAMES} frames" in out
  assert "after the SET press ended" not in out  # a step is not an engage attempt


@pytest.mark.parametrize("request_value, button", WHEEL)
def test_speed_step_never_resumes_or_sets_cruise_that_turned_off(capsys, request_value, button):
  buttons = CcOnlyRemoteButtons()
  assert buttons.update(request_value, True) == button
  assert buttons.update(0, True) == button
  assert _press(buttons, 0, False, CC_ONLY_SET_PRESS_FRAMES) == [NONE] * CC_ONLY_SET_PRESS_FRAMES
  assert "step stopped: factory cruise turned off" in capsys.readouterr().out


@pytest.mark.parametrize("request_value, button", WHEEL)
def test_brake_aborts_a_speed_step(request_value, button):
  buttons = CcOnlyRemoteButtons()
  assert buttons.update(request_value, True) == button
  buttons.abort()
  assert buttons.update(0, True) == NONE


@pytest.mark.parametrize("request_value, button, frames", [(REMOTE_CRUISE_RES_ACCEL_REQUEST, RES, CC_ONLY_PRESS_FRAMES),
                                                           (REMOTE_CRUISE_SET_DECEL_REQUEST, SET, CC_ONLY_SET_PRESS_FRAMES)])
def test_wheel_request_resumes_or_sets_while_cruise_is_off(request_value, button, frames):
  # the same press as cancel/resume and set at current speed, stopping once the lamp comes on
  assert _press(CcOnlyRemoteButtons(), request_value, False, frames + 20) == [button] * frames + [NONE] * 20
  buttons = CcOnlyRemoteButtons()
  assert buttons.update(request_value, False) == button
  assert buttons.update(0, True) == NONE


def _button_messages(cc_only, activate_cruise, lamp_on, brake=False, gas=False):
  packer = CANPacker("hyundai_kia_generic")
  spam_calls = []
  controller = SimpleNamespace(
    CP=SimpleNamespace(flags=HyundaiFlags.CC_ONLY_CAR.value if cc_only else 0),
    cc_only_remote_buttons=CcOnlyRemoteButtons(), packer=packer, frame=10, last_button_frame=0,
    make_spam_button=lambda CC, CS: spam_calls.append(1) or 0,
  )
  CS = SimpleNamespace(clu11=dict.fromkeys(CLU11_SIGNALS, 0),
                       out=SimpleNamespace(brakePressed=brake, gasPressed=gas, brakeHoldActive=False, parkingBrake=False,
                                           activateCruise=activate_cruise, cruiseLampOn=lamp_on))
  CC = SimpleNamespace(cruiseControl=SimpleNamespace(cancel=False, resume=False))
  sends = CarController.create_button_messages(controller, CC, CS, use_clu11=True)
  return sends, spam_calls


@pytest.mark.parametrize("request_value, lamp_on, button", [
  (REMOTE_CANCEL_REQUEST, True, CANCEL),
  (REMOTE_CRUISE_TOGGLE_REQUEST, True, CANCEL),
  (REMOTE_CRUISE_TOGGLE_REQUEST, False, RES),
  (REMOTE_CRUISE_SET_REQUEST, False, SET),
  (REMOTE_CRUISE_RES_ACCEL_REQUEST, True, RES),
  (REMOTE_CRUISE_RES_ACCEL_REQUEST, False, RES),
  (REMOTE_CRUISE_SET_DECEL_REQUEST, True, SET),
  (REMOTE_CRUISE_SET_DECEL_REQUEST, False, SET),
])
@pytest.mark.parametrize("gas", [False, True])  # unlike the brake, the accelerator never stops a press
def test_cc_only_remote_sends_one_clu11_button(request_value, lamp_on, button, gas):
  sends, spam_calls = _button_messages(cc_only=True, activate_cruise=request_value, lamp_on=lamp_on, gas=gas)
  assert len(sends) == 1
  addr, dat, bus = sends[0]
  # panda reads the CLU11 button from the low 3 bits of byte 0
  assert (addr, bus, dat[0] & 0x7) == (0x4F1, 0, button)
  assert spam_calls == []


@pytest.mark.parametrize("request_value", [REMOTE_CANCEL_REQUEST, REMOTE_CRUISE_TOGGLE_REQUEST, REMOTE_CRUISE_SET_REQUEST,
                                           REMOTE_CRUISE_RES_ACCEL_REQUEST, REMOTE_CRUISE_SET_DECEL_REQUEST])
@pytest.mark.parametrize("kwargs", [{"cc_only": False, "lamp_on": True}, {"cc_only": False, "lamp_on": False},
                                    {"cc_only": True, "lamp_on": True, "brake": True},
                                    {"cc_only": True, "lamp_on": False, "brake": True}])
def test_no_remote_button_without_cc_only_or_while_braking(request_value, kwargs):
  sends, _ = _button_messages(activate_cruise=request_value, **kwargs)
  assert sends == []
