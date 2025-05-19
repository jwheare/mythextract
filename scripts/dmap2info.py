#!/usr/bin/env python3
import sys
import os
import struct

import myth_headers
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

MAX_DTEX_TAGS_PER_DMAP = 128
DMAP_HEADER1_SIZE = 644
DmapHeader1Fmt = ('DmapHeader1', [
    ('B', 'width'),
    ('B', 'height'),
    ('B', 'indices'), # width*height
    ('x', None,),
    ('512s', 'dtex_ids', utils.list_pack(
        'DmapDtexIds', MAX_DTEX_TAGS_PER_DMAP, '>4s',
        filter_fun=lambda t: not utils.all_on(t)
    )),
    ('128s', 'scales', utils.list_pack(
        'DmapScales', MAX_DTEX_TAGS_PER_DMAP, '>B',
        filter_fun=lambda t: not utils.all_on(t)
    )), # pixels per cell
])

DMAP_HEADER2_SIZE = 256
DmapHeader2Fmt = ('DmapHeader2', [
    ('L', 'width'),
    ('L', 'height'),
    ('L', 'v_indices_offset'),
    ('4x', None),
    ('L', 't_indices_offset'),
    ('4x', None),
    ('L', 'entries_offset'),
    ('4x', None),
    ('224x', None),
])

DmapEntryFmt = ('DmapEntry', [
    ('4s', 'dtex_id'),
    ('B', 'pixels_per_cell'),
    ('B', 'r'),
    ('B', 'g'), 
    ('B', 'b'),
    ('24x', None),
    ('32s', 'name', utils.StringCodec),
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
    return myth_headers.parse_tag(DmapHeader1Fmt, data)

def parse_dmap_header2(data):
    return myth_headers.parse_tag(DmapHeader2Fmt, data)

def parse_dmap_tag(data):
    tag_header = myth_headers.parse_header(data)
    print(tag_header)
    if tag_header.version == 1:
        header = parse_dmap_header1(data)
        area = header.width * header.height
        print(header, area)
        v_indices_start = DMAP_HEADER1_SIZE + myth_headers.TAG_HEADER_SIZE
        v_indices_end = v_indices_start + area
        v_indices = data[v_indices_start:v_indices_end]
        entries = []
        for i, scale in enumerate(header.scales):
            if scale:
                DmapEntry = utils.make_nt(DmapEntryFmt)
                entry = DmapEntry(
                    dtex_id=header.dtex_ids[i],
                    pixels_per_cell=scale-1
                )
                entries.append(entry)
                print(entry)

        print('v_indices', v_indices[:32].hex())
    elif tag_header.version == 2:
        header = parse_dmap_header2(data)
        area = header.width * header.height
        print(header, area)

        entries = utils.list_codec(
            MAX_DTEX_TAGS_PER_DMAP, DmapEntryFmt,
            filter_fun=lambda _self, e: not utils.all_on(e.dtex_id) and not utils.all_off(e.dtex_id)
        )(data, offset=header.entries_offset)
        for entry in entries:
            if entry:
                print(
                    f'\x1b[48;2;{entry.r};{entry.g};{entry.b}m \x1b[0m '
                    f'{utils.decode_string(entry.dtex_id)} '
                    f'pixels_per_cell={entry.pixels_per_cell} '
                    f'desc={entry.name}'
                )

        v_indices_start = header.v_indices_offset + myth_headers.TAG_HEADER_SIZE
        v_indices_end = v_indices_start + area
        v_indices = data[v_indices_start:v_indices_end]
        print('v_indices', v_indices[:32].hex())

        t_indices_start = header.t_indices_offset + myth_headers.TAG_HEADER_SIZE
        t_indices_end = t_indices_start + (area * 2)
        t_indices = data[t_indices_start:t_indices_end]
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
