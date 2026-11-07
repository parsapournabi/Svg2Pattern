import re
import sys
import math
import argparse
import xml.etree.ElementTree as ET


TOKEN_PATTERN = re.compile(
    r'[a-zA-Z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?'
)

COMMANDS = {
    'M': 2, 'L': 2, 'H': 1, 'V': 1,
    'C': 6, 'S': 4, 'Q': 4, 'T': 2,
    'A': 7, 'Z': 0
}


# --------------------------------------------------
# Formatting
# --------------------------------------------------

def fmt(value):
    """Format a number as a GLSL float literal."""

    value = float(value)

    if abs(value) < 1e-12:
        value = 0.0

    result = f"{value:.9g}"

    if '.' not in result and 'e' not in result.lower():
        result += '.0'

    return result


def fmt_args(values):
    return ','.join(fmt(v) for v in values)


# --------------------------------------------------
# SVG Color
# --------------------------------------------------

NAMED_COLORS = {
    'black': '#000000',
    'white': '#ffffff',
    'red': '#ff0000',
    'green': '#008000',
    'blue': '#0000ff',
    'yellow': '#ffff00',
    'cyan': '#00ffff',
    'magenta': '#ff00ff',
    'gray': '#808080',
    'grey': '#808080',
    'orange': '#ffa500',
    'transparent': '#000000',
}


def parse_color(color):

    color = (color or '#000000').strip().lower()

    if color in NAMED_COLORS:
        color = NAMED_COLORS[color]

    if color.startswith('#'):

        h = color[1:]

        if len(h) == 3:
            h = ''.join(c * 2 for c in h)

        elif len(h) == 4:
            h = ''.join(c * 2 for c in h[:3])

        elif len(h) == 8:
            h = h[:6]

        if len(h) == 6:
            try:
                return f'0x{h.upper()}'
            except ValueError:
                pass

    # rgb(r,g,b)
    match = re.match(
        r'rgb\(\s*([\d.]+)%?\s*,\s*([\d.]+)%?\s*,\s*([\d.]+)%?\s*\)',
        color
    )

    if match:
        values = [
            max(0, min(255, round(float(v))))
            for v in match.groups()
        ]

        return '0x' + ''.join(f'{v:02X}' for v in values)

    return '0x000000'


def get_fill(element, inherited='#000000'):

    fill = element.get('fill', inherited)

    style = element.get('style', '')

    for item in style.split(';'):
        if ':' not in item:
            continue

        key, value = item.split(':', 1)

        if key.strip() == 'fill':
            fill = value.strip()

    return parse_color(fill)


# --------------------------------------------------
# Tokenizer
# --------------------------------------------------

def tokenize(data):

    tokens = []
    pos = 0

    for match in TOKEN_PATTERN.finditer(data):

        gap = data[pos:match.start()]

        if gap.strip(' \t\r\n,'):
            raise ValueError(f'Invalid SVG syntax: {gap}')

        tokens.append(match.group())
        pos = match.end()

    if data[pos:].strip(' \t\r\n,'):
        raise ValueError(f'Invalid SVG syntax: {data[pos:]}')

    return tokens


# --------------------------------------------------
# Arc -> Cubic Bezier
# --------------------------------------------------

def arc_to_cubic(x1, y1, rx, ry, rotation,
                 large_arc, sweep, x2, y2):

    rx = abs(rx)
    ry = abs(ry)

    if rx == 0 or ry == 0:
        return []

    if abs(x1 - x2) < 1e-12 and abs(y1 - y2) < 1e-12:
        return []

    phi = math.radians(rotation % 360.0)

    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    dx = (x1 - x2) * 0.5
    dy = (y1 - y2) * 0.5

    xp = cos_phi * dx + sin_phi * dy
    yp = -sin_phi * dx + cos_phi * dy

    # Correct radii if necessary
    lam = xp**2 / rx**2 + yp**2 / ry**2

    if lam > 1.0:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale

    rx2 = rx * rx
    ry2 = ry * ry

    numerator = rx2 * ry2 - rx2 * yp**2 - ry2 * xp**2
    denominator = rx2 * yp**2 + ry2 * xp**2

    factor = math.sqrt(max(0.0, numerator / denominator))

    if bool(large_arc) == bool(sweep):
        factor = -factor

    cxp = factor * (rx * yp / ry)
    cyp = factor * (-ry * xp / rx)

    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) * 0.5
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) * 0.5

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        cross = ux * vy - uy * vx
        return math.atan2(cross, dot)

    ux = (xp - cxp) / rx
    uy = (yp - cyp) / ry

    vx = (-xp - cxp) / rx
    vy = (-yp - cyp) / ry

    theta = math.atan2(uy, ux)
    delta = angle(ux, uy, vx, vy)

    if not sweep and delta > 0:
        delta -= 2.0 * math.pi

    elif sweep and delta < 0:
        delta += 2.0 * math.pi

    # Maximum 90 degrees per Bezier segment
    segments = max(1, math.ceil(abs(delta) / (math.pi * 0.5)))

    step = delta / segments

    def point(t):

        ct = math.cos(t)
        st = math.sin(t)

        return (
            cx + rx * cos_phi * ct - ry * sin_phi * st,
            cy + rx * sin_phi * ct + ry * cos_phi * st
        )

    def derivative(t):

        ct = math.cos(t)
        st = math.sin(t)

        return (
            -rx * cos_phi * st - ry * sin_phi * ct,
            -rx * sin_phi * st + ry * cos_phi * ct
        )

    result = []

    for i in range(segments):

        t1 = theta + i * step
        t2 = t1 + step

        alpha = 4.0 / 3.0 * math.tan(step / 4.0)

        p1 = point(t1)
        p2 = point(t2)

        d1 = derivative(t1)
        d2 = derivative(t2)

        c1 = (
            p1[0] + alpha * d1[0],
            p1[1] + alpha * d1[1]
        )

        c2 = (
            p2[0] - alpha * d2[0],
            p2[1] - alpha * d2[1]
        )

        # Preserve the exact final endpoint
        if i == segments - 1:
            p2 = (x2, y2)

        result.append((
            c1[0], c1[1],
            c2[0], c2[1],
            p2[0], p2[1]
        ))

    return result


# --------------------------------------------------
# SVG Path Parser
# --------------------------------------------------

def parse_path(data):

    tokens = tokenize(data)

    output = []

    i = 0
    command = None

    x = y = 0.0
    start_x = start_y = 0.0

    last_cubic = None
    last_quad = None

    def read(count):

        nonlocal i

        if i + count > len(tokens):
            raise ValueError('Not enough arguments')

        args = tokens[i:i + count]

        if any(v.isalpha() for v in args):
            raise ValueError('Invalid arguments')

        i += count

        return list(map(float, args))

    def emit(op, values):
        output.append(f'{op}({fmt_args(values)})')

    while i < len(tokens):

        if tokens[i].isalpha():

            command = tokens[i]
            i += 1

            if command.upper() not in COMMANDS:
                raise ValueError(f'Unsupported command: {command}')

        if command is None:
            raise ValueError('Expected SVG command')

        upper = command.upper()
        relative = command.islower()

        if upper == 'Z':

            output.append('z')

            x, y = start_x, start_y

            last_cubic = None
            last_quad = None

            command = None
            continue

        count = COMMANDS[upper]
        v = read(count)

        # ------------------------------------------
        # Move To
        # ------------------------------------------

        if upper == 'M':

            if relative:
                x += v[0]
                y += v[1]
                emit('m', v)
            else:
                x, y = v
                emit('M', v)

            start_x, start_y = x, y

            command = 'l' if relative else 'L'

            last_cubic = None
            last_quad = None

        # ------------------------------------------
        # Line To
        # ------------------------------------------

        elif upper == 'L':

            if relative:
                x += v[0]
                y += v[1]
                emit('l', v)
            else:
                x, y = v
                emit('L', v)

            last_cubic = None
            last_quad = None

        # ------------------------------------------
        # Horizontal Line
        # ------------------------------------------

        elif upper == 'H':

            if relative:
                x += v[0]
                emit('h', v)
            else:
                x = v[0]
                emit('H', v)

            last_cubic = None
            last_quad = None

        # ------------------------------------------
        # Vertical Line
        # ------------------------------------------

        elif upper == 'V':

            if relative:
                y += v[0]
                emit('v', v)
            else:
                y = v[0]
                emit('V', v)

            last_cubic = None
            last_quad = None

        # ------------------------------------------
        # Cubic Bezier
        # ------------------------------------------

        elif upper == 'C':

            ox, oy = x, y

            if relative:
                end_x = x + v[4]
                end_y = y + v[5]
                emit('c', v)
            else:
                end_x, end_y = v[4], v[5]
                emit('C', v)

            last_cubic = (v[2] + ox if relative else v[2],
                          v[3] + oy if relative else v[3])

            x, y = end_x, end_y
            last_quad = None

        # ------------------------------------------
        # Smooth Cubic Bezier
        # ------------------------------------------

        elif upper == 'S':

            ox, oy = x, y

            if last_cubic is not None:
                c1x = 2.0 * x - last_cubic[0]
                c1y = 2.0 * y - last_cubic[1]
            else:
                c1x, c1y = x, y

            if relative:
                c2x, c2y = x + v[0], y + v[1]
                end_x, end_y = x + v[2], y + v[3]
                op = 'c'
                values = (
                    c1x - ox, c1y - oy,
                    *v
                )
            else:
                c2x, c2y = v[0], v[1]
                end_x, end_y = v[2], v[3]
                op = 'C'
                values = (c1x, c1y, *v)

            emit(op, values)

            last_cubic = (c2x, c2y)

            x, y = end_x, end_y
            last_quad = None

        # ------------------------------------------
        # Quadratic Bezier -> Cubic Bezier
        # ------------------------------------------

        elif upper == 'Q':

            ox, oy = x, y

            if relative:
                qx, qy = x + v[0], y + v[1]
                end_x, end_y = x + v[2], y + v[3]
            else:
                qx, qy = v[0], v[1]
                end_x, end_y = v[2], v[3]

            c1x = x + 2.0 / 3.0 * (qx - x)
            c1y = y + 2.0 / 3.0 * (qy - y)

            c2x = end_x + 2.0 / 3.0 * (qx - end_x)
            c2y = end_y + 2.0 / 3.0 * (qy - end_y)

            emit('C', (
                c1x, c1y,
                c2x, c2y,
                end_x, end_y
            ))

            x, y = end_x, end_y

            last_quad = (qx, qy)
            last_cubic = None

        # ------------------------------------------
        # Smooth Quadratic Bezier
        # ------------------------------------------

        elif upper == 'T':

            if last_quad is not None:
                qx = 2.0 * x - last_quad[0]
                qy = 2.0 * y - last_quad[1]
            else:
                qx, qy = x, y

            if relative:
                end_x, end_y = x + v[0], y + v[1]
            else:
                end_x, end_y = v

            c1x = x + 2.0 / 3.0 * (qx - x)
            c1y = y + 2.0 / 3.0 * (qy - y)

            c2x = end_x + 2.0 / 3.0 * (qx - end_x)
            c2y = end_y + 2.0 / 3.0 * (qy - end_y)

            emit('C', (
                c1x, c1y,
                c2x, c2y,
                end_x, end_y
            ))

            x, y = end_x, end_y

            last_quad = (qx, qy)
            last_cubic = None

        # ------------------------------------------
        # Arc -> Cubic Bezier
        # ------------------------------------------

        elif upper == 'A':

            rx, ry, rotation, large_arc, sweep, ex, ey = v

            if relative:
                end_x = x + ex
                end_y = y + ey
            else:
                end_x, end_y = ex, ey

            curves = arc_to_cubic(
                x, y,
                rx, ry,
                rotation,
                int(large_arc),
                int(sweep),
                end_x, end_y
            )

            if not curves:

                if rx == 0 or ry == 0:
                    if relative:
                        emit('l', (ex, ey))
                    else:
                        emit('L', (end_x, end_y))

                # Identical endpoints produce no segment.

            else:

                for curve in curves:
                    emit('C', curve)

            x, y = end_x, end_y

            last_cubic = None
            last_quad = None

    return output


# --------------------------------------------------
# SVG Reader
# --------------------------------------------------

def process_element(element, inherited_fill='#000000'):

    fill = element.get('fill', inherited_fill)

    style = element.get('style', '')

    for item in style.split(';'):

        if ':' not in item:
            continue

        key, value = item.split(':', 1)

        if key.strip() == 'fill':
            fill = value.strip()

    tag = element.tag.split('}')[-1]

    if tag == 'path':

        data = element.get('d')

        if data:

            path_id = element.get('id', 'unnamed')
            color = parse_color(fill)

            print(f'\n// {path_id}')

            try:
                commands = parse_path(data)

                print(f'path( style(FILL,{color})')

                for cmd in commands:
                    print(f'    {cmd}')

                print(');')

            except Exception as error:
                print(f'// ERROR: {error}')

    for child in element:
        process_element(child, fill)


def process_svg(filename):

    tree = ET.parse(filename)
    root = tree.getroot()

    process_element(root)

    print('\n// SVG conversion finished')


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description='SVG to GLSL Path Converter'
    )

    parser.add_argument(
        'input',
        help='Input SVG file'
    )

    args = parser.parse_args()

    process_svg(args.input)


if __name__ == '__main__':
    main()

