import math

from cereal import car
from openpilot.common.params import Params
from openpilot.common.conversions import Conversions as CV
from openpilot.common.realtime import DT_CTRL

GearShifter = car.CarState.GearShifter

# carrot: low-speed turn assist (BlinkerForceTurn=2).
# The driving model often refuses to start a tight 90-degree turn (alleys/parking lots)
# even with a turn desire injected. This module cranks the desired curvature toward the
# driver's blinker directly, and hands off to the model once the car has rotated enough
# for the turn path to enter the camera's view - the same thing the driver was doing by
# starting the turn manually.
RAMP_RATE = 0.08            # curvature (1/m) added per second while ramping in
HANDOFF_FADE_RATE = 0.15    # curvature removed per second on handoff (~1s from full)
ABORT_FADE_RATE = 0.5       # curvature removed per second on abort (~0.3s from full)
DEBOUNCE_T = 0.3            # s the blinker must be on before engaging
MIN_SPEED_ON = 1.0 * CV.KPH_TO_MS
MAX_SPEED_ON = 20.0 * CV.KPH_TO_MS
MAX_SPEED_OFF = 25.0 * CV.KPH_TO_MS
PAUSE_SPEED = 0.5 * CV.KPH_TO_MS  # below this, hold state (waiting at a stop mid-turn)
PAUSE_RESET_T = 20.0        # give up after this long at a standstill
HANDOFF_ANGLE_DEG = 35.0    # rotation after which the model can see the turn path
ABORT_ANGLE_DEG = 90.0      # never rotate further than a full corner
TIMEOUT_T = 8.0             # max active time (excluding standstill pause)
# Level 3 only: the driver starts the turn themselves and the assist adds to it, instead
# of firing on the blinker alone. Matches the car's own steeringPressed threshold, so it
# takes a deliberate pull - not a hand resting on the wheel. Torque sign follows the same
# convention as curvature here: negative = left, positive = right.
TORQUE_ENGAGE = 150.0


class TurnAssist:
  def __init__(self):
    self.params = Params()
    self.frame = 0
    self.level = 0
    self.k_max = 0.15

    self.state = "idle"       # idle / ramp / fade
    self.armed = True         # re-engaging requires a fresh blinker off->on edge
    self.direction = 0.0      # -1 left, +1 right (this pipeline: negative desired curvature = left)
    self.assist_k = 0.0
    self.fade_rate = HANDOFF_FADE_RATE
    self.turned_deg = 0.0
    self.active_t = 0.0
    self.pause_t = 0.0
    self.blinker_t = 0.0

  def _update_params(self):
    if self.frame % 100 == 0:
      self.level = self.params.get_int("BlinkerForceTurn")
      self.k_max = min(max(self.params.get_float("TurnAssistMaxCurvature") * 0.01, 0.05), 0.25)
    self.frame += 1

  def _reset(self, rearm):
    self.state = "idle"
    self.assist_k = 0.0
    if rearm:
      self.armed = True

  def update(self, CS, lat_active, measured_curvature, desired_curvature):
    """Returns the (possibly overridden) desired curvature. Call at 100Hz before clip_curvature."""
    self._update_params()

    one_blinker = CS.leftBlinker != CS.rightBlinker
    # sign verified in-car: in this pipeline negative desired curvature = left turn
    cur_dir = -1.0 if CS.leftBlinker else 1.0

    if not one_blinker:
      self.armed = True
      self.blinker_t = 0.0
    else:
      self.blinker_t += DT_CTRL

    if self.level < 2 or not lat_active:
      self._reset(rearm=True)
      return desired_curvature

    v = CS.vEgo

    # level 2: engage on the blinker alone, with the driver's hands off.
    # level 3: engage only once the driver is actually pulling the wheel the way the
    # blinker points - we add to a turn they have started, rather than starting one for
    # them. This is also why level 3 cannot fire as they let go at the exit of a corner.
    if self.level >= 3:
      driver_ok = cur_dir * CS.steeringTorque >= TORQUE_ENGAGE
    else:
      driver_ok = not CS.steeringPressed

    if self.state == "idle":
      if (self.armed and one_blinker and self.blinker_t >= DEBOUNCE_T and
          MIN_SPEED_ON <= v <= MAX_SPEED_ON and
          driver_ok and
          CS.gearShifter == GearShifter.drive):
        self.state = "ramp"
        self.armed = False
        self.direction = cur_dir
        self.assist_k = 0.0
        self.turned_deg = 0.0
        self.active_t = 0.0
        self.pause_t = 0.0
      else:
        return desired_curvature

    # ---- active (ramp / fade) ----
    self.active_t += DT_CTRL

    # Driver steering input always wins, instantly. On level 3 that cannot mean any
    # torque at all - the driver is holding the wheel through the turn, which is what
    # engaged us - so only torque AGAINST the turn counts as them overriding.
    if (self.direction * CS.steeringTorque <= -TORQUE_ENGAGE) if self.level >= 3 else CS.steeringPressed:
      self._reset(rearm=False)
      return desired_curvature

    if self.state == "ramp":
      if (not one_blinker or cur_dir != self.direction or v > MAX_SPEED_OFF or
          self.turned_deg >= ABORT_ANGLE_DEG or self.active_t >= TIMEOUT_T):
        self.state = "fade"
        self.fade_rate = ABORT_FADE_RATE
      elif self.turned_deg >= HANDOFF_ANGLE_DEG:
        self.state = "fade"
        self.fade_rate = HANDOFF_FADE_RATE

    if v < PAUSE_SPEED:
      # holding at a stop mid-turn: freeze ramp/rotation/timeout
      self.pause_t += DT_CTRL
      self.active_t -= DT_CTRL
      if self.pause_t >= PAUSE_RESET_T:
        self._reset(rearm=False)
        return desired_curvature
    else:
      self.pause_t = 0.0
      # rotation progress from speed x measured curvature (unit/sign safe via abs)
      self.turned_deg += abs(v * measured_curvature) * DT_CTRL * 180.0 / math.pi
      if self.state == "ramp":
        self.assist_k = min(self.assist_k + RAMP_RATE * DT_CTRL, self.k_max)

    if self.state == "fade":
      self.assist_k -= self.fade_rate * DT_CTRL
      if self.assist_k <= 0.0:
        self._reset(rearm=False)
        return desired_curvature

    # blend: whichever pulls harder toward the turn direction wins,
    # so a committed model overrides the assist transparently
    return float(self.direction * max(self.direction * desired_curvature, self.assist_k))
