"""Simplified linear electromechanical actuator (EMA) model.

Representative only. The point of this project is the test method, not the plant.

Structure (per time step):
    position loop  ->  PI velocity demand  ->  load-dependent rate limit
    ->  first-order motor lag  ->  motor-side position  ->  backlash  ->  output rod

The actuator's own feedback is motor-side position (like a motor resolver).
The output rod position is what an independent "truth" sensor would measure.
That split is deliberate: the unit never grades itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EMAParams:
    stroke_mm: float = 25.0          # mechanical limit, +/- from neutral
    v0_mm_s: float = 40.0            # no-load max rate
    stall_force_n: float = 6500.0    # force at which extension rate drops to zero
    kp: float = 15.0                 # position loop gain, 1/s
    ki: float = 30.0                 # integral gain, 1/s^2 (removes droop under load)
    tau_motor_s: float = 0.010       # motor/velocity loop lag
    backlash_mm: float = 0.10        # total free play between motor and rod
    damping_n_s_per_mm: float = 13000.0 # back-drive under load causes slow droop
    supply_v_nominal: float = 28.0
    anti_windup: bool = False        # conditional integration (corrective action in RCA-001)
    n_motors: int = 2                # motors summing torque on one screw (stall force is the total)

    @classmethod
    def from_dict(cls, d: dict) -> "EMAParams":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EMAState:
    xm: float = 0.0       # motor-side position (unit's own feedback), mm
    x: float = 0.0        # output rod position (truth), mm
    v: float = 0.0        # motor-side velocity, mm/s
    integ: float = 0.0    # integrator state, mm*s


class EMA:
    """Discrete-time EMA. Call step(cmd, dt) at a fixed rate (1 kHz in this SIL).

    Load model: a constant opposing force `load_n` that resists extension
    (positive motion) and aids retraction. Supply sag scales the no-load rate.
    """

    def __init__(self, params: EMAParams | None = None, load_n: float = 0.0,
                 supply_v: float | None = None):
        self.p = params or EMAParams()
        self.load_n = load_n
        self.supply_v = supply_v if supply_v is not None else self.p.supply_v_nominal
        self.s = EMAState()
        self.motors_healthy = self.p.n_motors
        self.jammed = False
        self.drive_inhibited = False

    # ---- actuator-level faults (Part C) ----------------------------------
    def fail_motor(self) -> None:
        """Lose one motor channel. Stall force drops in proportion; no-load speed
        is unchanged because the remaining motor still turns the same screw."""
        self.motors_healthy = max(0, self.motors_healthy - 1)

    def jam(self) -> None:
        """Mechanical jam (screw/nut): output and motor side stop moving."""
        self.jammed = True

    def inhibit_drive(self) -> None:
        """Monitor response: remove motor drive and stop integrating."""
        self.drive_inhibited = True

    @property
    def stall_force_effective(self) -> float:
        return self.p.stall_force_n * self.motors_healthy / self.p.n_motors

    # ---- characteristics -------------------------------------------------
    def v_max(self, direction: float) -> float:
        """Achievable rate in a given direction under the current load and supply."""
        v0 = self.p.v0_mm_s * (self.supply_v / self.p.supply_v_nominal)
        if direction > 0:   # extending against the load
            stall = self.stall_force_effective
            if stall <= 0.0:
                return 0.0
            return max(0.0, v0 * (1.0 - self.load_n / stall))
        return v0           # retracting, load aids; capped at no-load rate

    # ---- simulation ------------------------------------------------------
    def reset(self, position_mm: float = 0.0) -> None:
        self.s = EMAState(xm=position_mm, x=position_mm)
        # pre-load the integrator so a loaded actuator starts in equilibrium
        droop = self.load_n / self.p.damping_n_s_per_mm
        self.s.integ = droop / self.p.ki if self.p.ki else 0.0

    def step(self, cmd_mm: float, dt: float) -> float:
        p, s = self.p, self.s
        err = cmd_mm - s.xm                      # loop closes on the unit's OWN sensor
        raw = p.kp * err + p.ki * (s.integ + err * dt)
        lim_hi, lim_lo = self.v_max(1.0), -self.v_max(-1.0)
        saturated = raw > lim_hi or raw < lim_lo
        if not (p.anti_windup and saturated) and not self.drive_inhibited:
            s.integ += err * dt                  # baseline design integrates through saturation
        demand = max(lim_lo, min(lim_hi, p.kp * err + p.ki * s.integ))
        if self.drive_inhibited:
            demand = 0.0
        self.last_demand = demand

        if self.jammed:                          # nothing moves, whatever the demand
            s.v = 0.0
            return s.x

        s.v += (demand - s.v) * (dt / p.tau_motor_s)
        droop = self.load_n / p.damping_n_s_per_mm   # load back-drives toward retract
        s.xm += (s.v - droop) * dt

        # mechanical end stops
        if s.xm > p.stroke_mm:
            s.xm, s.v = p.stroke_mm, min(s.v, 0.0)
        elif s.xm < -p.stroke_mm:
            s.xm, s.v = -p.stroke_mm, max(s.v, 0.0)

        # backlash: rod only moves once the motor side takes up the free play
        half = p.backlash_mm / 2.0
        if s.xm - s.x > half:
            s.x = s.xm - half
        elif s.xm - s.x < -half:
            s.x = s.xm + half
        return s.x

    @property
    def position(self) -> float:
        """Output rod position (what the independent truth sensor reads)."""
        return self.s.x

    @property
    def own_feedback(self) -> float:
        """Motor-side position (what the actuator's own sensor reports)."""
        return self.s.xm
