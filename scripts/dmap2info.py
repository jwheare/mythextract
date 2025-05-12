#!/usr/bin/env python3
from collections import namedtuple
import sys
import os
import struct

import myth_headers
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

MAX_DTEX_TAGS_PER_DMAP = 128
DMAP_HEADER1_SIZE = 644
DmapHeader1Fmt = """>
    B B
    B
    x
    512s
    128s
"""
DmapHeader1 = namedtuple('DmapHeader1', [
    'width', 'height',
    'indices', # width*height
    'dtex_ids',
    'scales', # pixels per cell
])

DMAP_HEADER2_SIZE = 256
DmapHeader2Fmt = """>
    L L
    L
    4x
    L
    4x
    L
    4x
    224x
"""
DmapHeader2 = namedtuple('DmapHeader2', [
    'width', 'height',
    'v_indices_offset',
    't_indices_offset',
    'entries_offset',
])

DMAP_ENTRY_SIZE = 64
DmapEntryFmt = """>
    4s
    B
    B B B
    24x
    32s
"""
DmapEntry = namedtuple('DmapEntry', [
    'dtex_id',
    'pixels_per_cell',
    'r', 'g', 'b',
    'name',
])

def main(dmap_tag):
    """
    Show info stored in detail map tags
    """
    try:
        data = utils.load_file(dmap_tag)
        parse_dmap_tag(data)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_dmap_header1(data):
    dmap_header1 = DmapHeader1._make(struct.unpack(DmapHeader1Fmt, data[:DMAP_HEADER1_SIZE]))
    return dmap_header1._replace(
        dtex_ids=[t if not utils.all_on(t) else None for t in struct.unpack(f'>{MAX_DTEX_TAGS_PER_DMAP*"4s"}', dmap_header1.dtex_ids)],
        scales=[t if not utils.all_on(t) else None for t in struct.unpack(f'>{MAX_DTEX_TAGS_PER_DMAP*"B"}', dmap_header1.scales)],
    )
def parse_dmap_header2(data):
    return DmapHeader2._make(struct.unpack(DmapHeader2Fmt, data[:DMAP_HEADER2_SIZE]))

def parse_dmap_tag(data):
    tag_header = myth_headers.parse_header(data)
    print(tag_header)
    tag_data = data[myth_headers.TAG_HEADER_SIZE:]
    if tag_header.version == 1:
        header = parse_dmap_header1(tag_data)
        area = header.width * header.height
        print(header, area)
        v_indices_start = DMAP_HEADER1_SIZE
        v_indices_end = v_indices_start + area
        v_indices = tag_data[v_indices_start:v_indices_end]
        entries = []
        for i, scale in enumerate(header.scales):
            if scale:
                entry = DmapEntry._make(header.dtex_ids[i], scale-1, None, None, None, None)
                entries.append(entry)
                print(entry)

        print('v_indices', v_indices[:32].hex())
    elif tag_header.version == 2:
        header = parse_dmap_header2(tag_data)
        area = header.width * header.height
        print(header, area)

        entries = []
        for values in utils.iter_unpack(
            header.entries_offset,
            MAX_DTEX_TAGS_PER_DMAP,
            DmapEntryFmt,
            data
        ):
            entry = DmapEntry._make(values)
            if not utils.all_on(entry.dtex_id) and not utils.all_off(entry.dtex_id):
                entries.append(entry)
                print(
                    f'\x1b[48;2;{entry.r};{entry.g};{entry.b}m \x1b[0m '
                    f'{utils.decode_string(entry.dtex_id)} '
                    f'pixels_per_cell={entry.pixels_per_cell} '
                    f'desc={utils.decode_string(entry.name)}'
                )

        v_indices_start = header.v_indices_offset
        v_indices_end = v_indices_start + area
        v_indices = tag_data[v_indices_start:v_indices_end]
        print('v_indices', v_indices[:32].hex())

        t_indices_start = header.t_indices_offset
        t_indices_end = t_indices_start + (area * 2)
        t_indices = tag_data[t_indices_start:t_indices_end]
        print('t_indices', t_indices[:32].hex())
    else:
        print('Invalid detail map version', tag_header.version)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 dmap2info.py <dmap_tag>")
        sys.exit(1)
    
    dmap_tag = sys.argv[1]

    try:
        main(dmap_tag)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
