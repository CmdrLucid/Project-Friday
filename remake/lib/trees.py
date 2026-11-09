"""Measured TREE SHAPES shared by the light proxies (remake/recipes/proxy_*.py) and the remake assets (user 2026-11-09: 'wir brauchen es spaeter
fuers Remake - direkt so umsetzen, dass es wiederverwendbar wird/bleibt').  A tree here is ROUND (a solid of revolution): the remake camera turns in
90 degree steps (remake/README.md), so a shape flattened to fit one drawing would look thin from the side.  Profiles are (height above the ground,
radius) bottom to top in world units, measured on the original picture; a remake asset dresses the same profile (foliage tiers, bark, roots),
the light uses it bare.  No Blender needed here (pure geometry, see proxy.revolve)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# BIG TREE of room 488 (ROUTE_AFTER_DESTEL_2), axis x 576 y 656 on ground 128 (walkable cells 34..37 x 39..42), measured 2026-11-09:
# the drawn crown's layer A half width per picture row (V 408 tip .. 489, 27 rows) fitted by a round crown (screen half width of a ring of
# radius r at height z: sqrt 2 * r * sqrt(1 - ((V - (616 - z)) * sqrt 2 / r) ^ 2)); rows match within 1..3 px (5 at one drawn tier edge, V 423).
# Trunk radius 5 up to 10, the crown's flat underside at 10..12 (the roots are drawn below it). From the game camera the round crown's
# underside lies over the drawn roots (V 495..503): the sprite is drawn from a lower angle than the 2:1 view, no round tree fits both.
BIG_TREE_488 = [(0, 5.0), (10, 5.0), (12, 38.0), (16, 43.0), (22, 39.0), (28, 34.0), (34, 29.0), (42, 27.0), (48, 21.0), (56, 17.0),
                (62, 11.0), (68, 7.0), (74, 4.0), (80, 0.0)]

def round_tree(name, cx, cy, z0, profile, n=16):
    """the profile as ONE closed light / remake mesh standing at (cx, cy, z0) (proxy.revolve: outward faces, no inner caps)"""
    import proxy
    return proxy.revolve(name, cx, cy, [(z0 + h, max(r, 0.05)) for h, r in profile], n=n)
