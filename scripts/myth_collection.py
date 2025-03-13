#!/usr/bin/env python3
from collections import namedtuple
import struct

import myth_headers

# collection_tag
# 616C7269

# number_of_permutations
# 0001

# 0000
# tint_fraction

# 5 permutations x 8 hue changes
# rrrrggggbbbbflag
# E600F300F3000004
# D100100010000004
# 000000FF01FFFFFF
# 0000271000002711
# 0453E56804526718
# 0453E52400000000
# FFFFFE580453F4C8
# 6665746300010000

# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000

# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000

# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000

# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000
# 0000000000000000


# tint_color
# rrrrggggbbbbflag
# CC00FF00FE000000

# unused
# 000000000000000000000000000000000000000000000000000000000000000000000000

# runtime data
# 0000
# 0000 0000 0000 0000 0000

CollectionRefFmt = """>
    4s
    H H
    320s
    8s
    36x
    2x 10x
"""
CollectionRef = namedtuple('CollectionRef', [
    'collection_tag',
    'number_of_permutations', 'tint_fraction',
    'colors',
    'tint'
])

def parse_color(data):
    (r, g, b, flags) = struct.unpack(">H H H H", data)
    return (r, g, b, flags)

def parse_collection_ref(data):
    colref = CollectionRef._make(struct.unpack(CollectionRefFmt, data))
    return colref._replace(
        collection_tag=myth_headers.decode_string(colref.collection_tag),
        colors=parse_hue_permutations(colref),
        tint=parse_color(colref.tint)
    )

def parse_hue_permutations(colref):
    color_size = 8
    hue_len = 8
    hue_start = 0
    perms = []
    for perm_i in range(colref.number_of_permutations):
        hues = []
        for hue_i in range(hue_len):
            hue_end = hue_start + color_size
            (r, g, b, flags) = parse_color(colref.colors[hue_start:hue_end])
            hues.append((r, g, b, flags))
            hue_start = hue_end
        perms.append(hues)
    return perms
