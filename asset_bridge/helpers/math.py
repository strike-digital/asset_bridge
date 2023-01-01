from mathutils import Vector as V


def lerp(fac, a, b):
    """Linear interpolation between a and b."""
    return a + (b - a) * fac


def vec_lerp(fac, a, b):
    """Linear interpolation between points a and b"""
    return V(lerp(fac, i, j) for i, j in zip(a, b))
