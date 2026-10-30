# References

Public sources used to size and scope this project, and what each one informed. Nothing here comes from non-public material. This project does not model any company's actual actuator or architecture.

## Actuator force class

The flight-class actuator is sized to a representative electromechanical flight-control actuator class, over 1,000 lbf: stall force and rated load in `config/sil.yaml` (rated 4,550 N, about 1,020 lbf). Background on redundant EMA architectures (multiple motors on one screw, jam tolerance) is in the review listed under Force fight below. Values are representative and do not model any specific product.

## Force fight and equalization (R13)

| Source | What it informed |
| --- | --- |
| [US 11,745,858 B2, "Managing force equalization via force-fight cycle detection" (Bell / Textron)](https://patents.google.com/patent/US11745858) | Monitor design: compare each actuator's force to the mean of the others, threshold plus persistence, then disengage. The patent counts fight cycles; this project uses a simpler threshold-and-persistence monitor. |
| [Kowalski et al., "Force Fight Compensation for Redundant Electro-Mechanical Flight Control Actuators," ICAS 2018 (DLR / Liebherr)](https://www.icas.org/icas_archive/ICAS2018/data/papers/ICAS2018_0271_paper.pdf) | Electric actuators running active/active on one surface need force-fight compensation. |
| [Li, Lin, Tian, "Force fighting equalisation for aircraft rudder's triple active actuation system," Aeronautical Journal, 2022](https://cambridge.org/core/journals/aeronautical-journal/article/abs/research-and-modeling-of-force-fighting-equalisation-for-aircraft-rudders-triple-active-actuation-system/F9555CCC8F849A2DE75379BF32FD5BE9) | Triple-active actuation on one surface, equalization to minimize fight force. |
| [Hall et al., "Investigating Actuation Force Fight with Asynchronous and Synchronous Redundancy Management Techniques" (Honeywell / SRI for NASA)](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20130012913.pdf) | Force fight from timing and command disagreement between redundant channels. |
| [Progress in Redundant Electromechanical Actuators for Aerospace Applications (review)](https://www.open-access.bcu.ac.uk/14809) | Background on redundant EMA architectures (torque-summed and force-summed). |

## Bench actuator (model correlation, M1)

| Source | What it informed |
| --- | --- |
| [Actuonix L16 datasheet (PDF)](https://cdn.robotshop.com/media/F/Fir/RB-Fir-111/pdf/ActuonixL16Datasheet.pdf) | L16-P profile, 35:1 gear: 32 mm/s no load, 50 N @ 16 mm/s, 24 N @ 24 mm/s, 0.25 mm backlash, 0.3 mm repeatability, pot linearity < 2 %, 12 V. |
| [Actuonix L16-P 100 mm 35:1 12 V (RobotShop)](https://www.robotshop.com/products/actuonix-l16-linear-actuator-100mm-351-12v-w-potentiometer-feedback) | Part selected for the desk rig. |
