"""Two-link authoring primitive for a declared 2D target, not a walk generator.

Return relative clockwise angles in the splitter's screen-y-down convention for
two rest links pointing down. Reject unreachable targets rather than silently
changing the intended contact or bone length. Caller owns timing and targets.
"""
import math


def solve_two_link(dx, dy, upper, lower, bend=1):
    values=(dx,dy,upper,lower)
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in values):
        raise ValueError('Finite numeric target and lengths required')
    if upper<=0 or lower<=0 or bend not in (-1,1):
        raise ValueError('Positive lengths and bend sign +/-1 required')
    r=math.hypot(dx,dy)
    if not math.isfinite(r) or r==0:
        raise ValueError('Unreachable or ambiguous two-link target')
    scale=max(r,upper,lower)
    rn,u,l=r/scale,upper/scale,lower/scale
    if rn>u+l+1e-12 or rn<abs(u-l)-1e-12 or min(rn,u,l)==0:
        raise ValueError('Unreachable or ambiguous two-link target')
    clamp=lambda x:max(-1.,min(1.,x))
    alpha=math.acos(clamp((rn*rn+u*u-l*l)/(2*rn*u)))
    internal=math.acos(clamp((u*u+l*l-rn*rn)/(2*u*l)))
    a=math.atan2(dy,dx)-bend*alpha
    relative=bend*(math.pi-internal)
    result=(math.degrees(a)-90,math.degrees(relative))
    if not all(math.isfinite(v) for v in result):raise ValueError('Nonfinite IK result')
    return result
