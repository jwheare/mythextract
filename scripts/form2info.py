#!/usr/bin/env python3
import sys
import os
import struct
import random

import myth_headers

DEBUG = (os.environ.get('DEBUG') == '1')

def main(form_tag, num_units):
    """
    Show info stored in formations tag file
    """

    try:
        data = myth_headers.load_file(form_tag)
        parse_form_file(data, num_units)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

FORMATIONS = [
    'Short Line',
    'Long Line',
    'Loose Line',
    'Staggered Line',
    'Box',
    'Rabble',
    'Shallow Encirclement',
    'Deep Encirclement',
    'Vanguard',
    'Circle',
]

def dist(val):
    return round(val/512, 2)

def angle(val):
    return round(val / (0xffff / 360), 2)

UNIT = '\x1b[93m◉\x1b[0m'

def parse_form_file(data, units):
    header = myth_headers.parse_header(data)
    print(header)
    form_data = data[myth_headers.TAG_HEADER_SIZE:]

    (
        short_line_row, short_line_separation,
        long_line_row, long_line_separation,
        loose_line_row, loose_line_separation,
        staggered_line_row, staggered_line_separation,
        box_separation,
        rabble_separation, rabble_x_bias,
        min_encircle_radius, encircle_separation,
        shallow_encircle_arc, deep_encircle_arc,
        vanguard_front_separation, vanguard_separation, vanguard_row_separation,
        circle_separation
    ) = struct.unpack(""">
        H H
        H H
        H H
        H H
        H
        H H
        H H
        H H
        H H H
        H
        2x
    """, form_data)

    formations = [
        (short_line_row, dist(short_line_separation)),
        (long_line_row, dist(long_line_separation)),
        (loose_line_row, dist(loose_line_separation)),
        (staggered_line_row, dist(staggered_line_separation)),
        (dist(box_separation),),
        (dist(rabble_separation), dist(rabble_x_bias)),
        (
            dist(min_encircle_radius), dist(encircle_separation),
            angle(shallow_encircle_arc)
        ),
        (
            dist(min_encircle_radius), dist(encircle_separation),
            angle(deep_encircle_arc)
        ),
        (
            dist(vanguard_front_separation), dist(vanguard_separation),
            dist(vanguard_row_separation)
        ),
        (dist(circle_separation))
    ]

    for f_i, form in enumerate(formations):
        print(f'{(f_i+1):<2} {FORMATIONS[f_i]:<20} {form}')
        if f_i < 6:
            # lines/box
            if f_i == 4:
                # box
                units_per_row = round(units ** 0.5)
                separation = form[0]
            elif f_i == 5:
                # rabble
                separation = random.randint(1, 20) / (form[0] * 3)
            else:
                # lines
                units_per_row = form[0]
                separation = form[1]
            sep = round(separation/1)
            rows = []
            row = []
            rows.append(row)
            max_upr = 0
            for u in range(units):
                if f_i == 3 and len(rows) % 2 == 0:
                    # staggered
                    upr = units_per_row + 1
                elif f_i == 5:
                    upr = random.randint(1, round(units/2))
                else:
                    upr = units_per_row
                if upr > max_upr:
                    max_upr = upr
                row.append(upr)
                if len(row) >= upr:
                    row = []
                    rows.append(row)
            for row_i, row in enumerate(rows):
                if f_i == 5:
                    # rabble
                    offset = round(random.randint(1, 20) / (form[0] * 3))
                    unit_row = f"{offset * ' '}"
                    for upr in row:
                        rabble_sep = round(random.randint(1, 20) / (form[0] * 3))
                        unit_row += f"{rabble_sep * ' '}{UNIT}"
                    print(unit_row)
                else:
                    offset = 0
                    row_diff = 0
                    if len(row):
                        row_diff = max_upr - len(row)
                    if row_diff > 0:
                        offset = round((row_diff * (sep + 1)) / 2)
                    elif f_i == 3 and row_i % 2 == 0:
                        # staggered
                        offset = round(sep / 2)
                    unit_row = f"{offset * ' '}"
                    for upr in row:
                        unit_row += f"{UNIT}{sep * ' '}"
                    print(unit_row)
                    for line_sep in range(round(sep/2)-1):
                        print()
        # elif i == 4:
        #     # box

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 form2info.py <form_tag> [<num_units>]")
        sys.exit(1)
    
    form_tag = sys.argv[1]

    num_units = 16
    if len(sys.argv) > 2:
        num_units = int(sys.argv[2])

    try:
        main(form_tag, num_units)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
