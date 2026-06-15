"""
    Written By Ettore Caccioli
    © 2026 Wheelchair Karting
"""


PRECISION = 4

def print_core_hello():
    print("===   ©   Wheelchair Karting® 2026     ===")
    print(" *                                      *")
    print(" *         DeltaKart Core V3.0          *")
    print(" *                                      *")
    print("====== Written by Ettore Caccioli =======")

def get_curve(p_mid: tuple[float, float] = None, x_max=100, y_min=0, y_max=255):
    """
        Function to calculate the proper sensibility curve for
        the joystick.

        Returns: (a, x_seg1), (a1, b, x_seg2)
    """
    
    if p_mid is not None:
        x, y = p_mid
        a = round(1/((x**2)/y), PRECISION)
    else:
        a = round(1/(((x_max-1)**2/y_max)), PRECISION)
        return (a, x_max),(0,0,0)

    b = round((y*(x_max**2) - y_max*(x**2))/(x*(x_max**2)-x_max*(x**2)), PRECISION)

    a1 = round((y - b*x) / (x**2), PRECISION)

    return ((a, x), (a1, b, x_max))

def apply_curve(curve: tuple[tuple[float, float], tuple[float, float, float]], X):
    seg1, seg2 = curve
    a, x_max1 = seg1
    a1, b, x_max2 = seg2

    if abs(X) <= x_max1:
        return -1  if X < 0 else 1, int(min(round(a*(abs(X)**2), PRECISION),255))
    elif abs(X) <= x_max2:
        return -1  if X < 0 else 1, int(min(round(a1*(abs(X)**2) + b*abs(X), PRECISION),255))

def handler(sig, frame):
    print("SIGTERM_QUIT!")
    import sys
    sys.exit(0)

def htons(x, format='big'):
    if format == 'little': return [(x & 0xFF), ((x >> 8) & 0xFF)] if type(x) is int else [(ord(x) & 0xFF), ((ord(x) >> 8) & 0xFF)]
    if format == 'big': return [((x >> 8) & 0xFF), (x & 0xFF)] if type(x) is int else [((ord(x) >> 8) & 0xFF), (ord(x) & 0xFF)]
    return -1

def twos_complement(val, bits) -> int:
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val


if __name__ == "__main__":
    power_mode = get_curve((60,100))
    normal_mode = get_curve((50,75), y_max=150)
    precision_mode = get_curve(y_max=100)

    print([apply_curve(precision_mode, i) for i in range(-100, 100)])


