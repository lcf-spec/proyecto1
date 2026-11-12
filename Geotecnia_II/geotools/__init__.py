"""geotools - core geotechnical engineering calculations.

Units everywhere: kN, m, kPa, kN/m^3, angles in degrees.
"""
from . import bearing, classification, consolidation, earth_pressure, piles, slopes, stresses

GAMMA_W = 9.81  # kN/m^3

__all__ = ["bearing", "classification", "consolidation", "earth_pressure",
           "piles", "slopes", "stresses", "GAMMA_W"]
