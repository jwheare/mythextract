#!/usr/bin/env python3
from collections import namedtuple
import enum
import os
import struct

import myth_headers
import utils

DEBUG_COLL = (os.environ.get('DEBUG_COLL') == '1')

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

D256HeadSize = 64
D256HeadFmt = """>
    L
    4s
    L L L
    20x
    L L L
    L L L
"""
D256Head = namedtuple('D256Head', [
    'flags',
    'tag_id',
    'ref_count', 'ref_offset', 'ref_size',
    'data_offset', 'data_size', 'data_delta',
    'hue_change_count', 'hue_changes_offset', 'hue_changes_size'
])

D256RefFmt = """>
    64s
    L L
    8x
    H H

    L

    H H
    H H
    L

    H H
    L

    20x
"""
class D256RefFlags(enum.Flag):
    UNMIRROR = enum.auto()

D256Ref = namedtuple('D256Ref', [
    'name',
    'offset', 'size',
    'width', 'height',

    'original_checksum',

    'original_reference_point_x', 'original_reference_point_y',
    'detail_reference_point_x', 'detail_reference_point_y',
    'detail_pixels_to_world',

    'original_width', 'original_height',
    'flags',
])

HueChangeFmt = """>
    64s
    H H
    32s
    H H
    H
    6x
    16x
"""
HueChange = namedtuple('HueChange', [
    'name',
    'hue0', 'hue1',
    'colors_effected',
    'minimum_saturation', 'median_hue',
    'flags',
])

Header256Size = 320
Header256Fmt = """>
    I I
    56x

    I I I I
    I I I I
    I I I I
    I I I I
    I I I I
    I I I I
    I I I I
    I I I I
    
    I I
    48x
    I I I I
    40x
    16x
"""
Header256 = namedtuple("Header256", [
    'flags',
    'user_data',
    'color_table_count', 'color_tables_offset', 'color_tables_size', 'color_tables',
    'hue_change_count', 'hue_changes_offset', 'hue_changes_size', 'hue_changes',
    'bitmap_reference_count', 'bitmap_references_offset', 'bitmap_references_size', 'bitmap_references',
    'bitmap_instance_count', 'bitmap_instances_offset', 'bitmap_instances_size', 'bitmap_instances',
    'sequence_reference_count', 'sequence_references_offset', 'sequence_references_size', 'sequence_references',
    'shadow_map_count', 'shadow_maps_offset', 'shadow_maps_size', 'shadow_maps',
    'blend_table_count', 'blend_tables_offset', 'blend_tables_size', 'blend_tables',
    'remapping_table_count', 'remapping_tables_offset', 'remapping_tables_size', 'remapping_tables',
    'shading_table_count', 'shading_table_pointers',
    'data_offset', 'data_size', 'data_delta', 'data',
])

BITMAP_META_SIZE = 52
BitmapMetaFmt = """>
    H H
    h
    H
    H
    H H
    H
    H
    34x
"""
BitmapMeta = namedtuple('BitmapMeta', [
    'width', 'height',
    'bytes_per_row',
    'flags',
    'logical_bit_depth',
    'width_bits', 'height_bits',
    'pixel_upshift',
    'encoding',
])

class Encoding(enum.Enum):
    ORIGINAL = 0
    EXT_R8G8B8A5H = 1
    EXT_ARGB_8888_32 = enum.auto()
    EXT_RGB_888_24 = enum.auto()

class BitmapFlags(enum.Flag):
    POWER_OF_TWO = enum.auto()
    BITMAP_COLOR_KEY_TRANSPARENCY = enum.auto()
    TRANSPARENCY_ENCODED_1BIT = enum.auto()
    LIGHT_MASK_ENCODED_4BIT = enum.auto()
    TRANSPARENCY_ENCODED_4BIT = enum.auto()
    NO_ROW_ADDRESS_TABLE = enum.auto()
    WORD_ALIGNED_ENCODING = enum.auto()
    GRAYSCALE_BITMAP = enum.auto()
    PIXEL_FREE = enum.auto()
    POSTPROCESSED_BITMAP = enum.auto()
    PROTECTED_BITMAP = enum.auto()
    BITMAP_IS_OVERLAY = enum.auto()
    BITMAP_CHANGED = enum.auto()
    BITMAP_IN_COLLECTION = enum.auto()
    BITMAP_EXTENDED_ENCODING = enum.auto()

ANGLE_SF = (0xffff / 360)
FIXED_SF = 1 << 16

def parse_color(data):
    (r, g, b, flags) = struct.unpack(">H H H H", data)
    return (r, g, b, flags)

def parse_collection_ref(data):
    colref = CollectionRef._make(struct.unpack(CollectionRefFmt, data[64:]))
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
            hues.append(parse_color(colref.colors[hue_start:hue_end]))
            hue_start = hue_end
        perms.append(hues)
    return perms

def word_align(value):
    return value + (value & 1)

def parse_color_table(data, coll_header):
    color_table_start = coll_header.data_offset + coll_header.color_tables_offset
    color_table_end = color_table_start + coll_header.color_tables_size
    color_table_data = data[color_table_start:color_table_end]
    color_table_head_end = 32
    (ct_count, ct_unused) = struct.unpack('>I 28s', color_table_data[:color_table_head_end])
    
    if DEBUG_COLL:
        print(f'color table {ct_count}')
    
    color_table = []
    for cc, (r, g, b, cc_flags) in enumerate(utils.iter_unpack(
        color_table_head_end, ct_count,
        '>Bx Bx Bx H', color_table_data
    )):
        color_table.append((r, g, b, cc_flags))
        if DEBUG_COLL:
            print(f'\x1b[48;2;{r};{g};{b}m  \x1b[0m', end='')
            if (cc == (ct_count - 1) or (cc % 25) == 24):
                print()
    return color_table

BitmapInstanceFmt = """>
    L

    8x
    H H

    8x
    H H

    H
    H
    l
    H H

    8x
    16x
"""
BitmapInstance = namedtuple('BitmapInstance', [
    'flags',
    'reg_point_x', 'reg_point_y',
    'key_point_x', 'key_point_y',
    'bitmap_index',
    'highres_bitmap_index',
    'highres_pixels_to_world',
    'highres_reg_point_x', 'highres_reg_point_y',
])

def parse_bitmap_instance(data, coll_header):
    bitmap_indices = []
    bitmap_instance_start = coll_header.data_offset + coll_header.bitmap_instances_offset
    for values in utils.iter_unpack(
        bitmap_instance_start, coll_header.bitmap_instance_count,
        BitmapInstanceFmt, data
    ):
        bitmap_instance = BitmapInstance._make(values)
        bitmap_indices.append(bitmap_instance.bitmap_index)
    return bitmap_indices

SEQ_DATA_SIZE = 64
SequenceDataFmt = """>
    L
    l
    h
    h
    h
    h
    h
    3h
    4s 4s 4s
    h
    h
    l
    l
    l
    h
    h
    h
    6x
"""
SequenceData = namedtuple('SequenceData', [
    'flags',
    'pixels_to_world',
    'number_of_views',
    'frames_per_view',
    'ticks_per_frame',
    'key_frame',
    'loop_frame',
    'sound_index_first',
    'sound_index_key',
    'sound_index_last',
    'sound_tag_first',
    'sound_tag_key',
    'sound_tag_last',
    'transfer_mode',
    'transfer_period',
    'radius',
    'height0',
    'height1',
    'world_radius',
    'world_height0',
    'world_height1',
])

def parse_sequences(data, coll_header):
    sequences = []
    if coll_header.sequence_reference_count:
        sequence_reference_start = coll_header.data_offset + coll_header.sequence_references_offset
        for i, (seq_name, seq_offset, seq_size, seq_unused) in enumerate(utils.iter_unpack(
            sequence_reference_start, coll_header.sequence_reference_count,
            '>64s I I 56s', data
        )):
            seq_start = coll_header.data_offset + seq_offset
            seq_end = seq_start + SEQ_DATA_SIZE
            seq_data = SequenceData._make(
                struct.unpack_from(SequenceDataFmt, data, offset=seq_start)
            )

            instances_indices = []
            for (
                shadow_map_index,
                key_point_x, key_point_y, key_point_z,
                bitmap_instance_index
            ) in utils.iter_unpack(
                seq_end, seq_data.frames_per_view,
                '>H H H H 38x H', data
            ):
                instances_indices.append(bitmap_instance_index)

            name = myth_headers.decode_string(seq_name)
            if DEBUG_COLL:
                print(
                    f'{i:>2} sequence: {name:<32} '
                    f'instance indices1: {instances_indices}'
                )
            sequences.append({
                'name': name,
                'instance_indices': instances_indices,
                'metadata': seq_data,
            })

    return sequences

BitmapReferenceFmt = """>
    64s
    I I
    H H
    H H
    32x
    16x
"""
BitmapReference = namedtuple('BitmapReference', [
    'name',
    'offset', 'size',
    'data_1', 'data_2',
    'width', 'height',
])

def parse_bitmaps(data, coll_header, color_table):
    bitmaps = []
    bitmap_reference_start = coll_header.data_offset + coll_header.bitmap_references_offset
    for i, values in enumerate(utils.iter_unpack(
        bitmap_reference_start, coll_header.bitmap_reference_count,
        BitmapReferenceFmt, data
    )):
        bitref = BitmapReference._make(values)
        bitref = bitref._replace(
            name=myth_headers.decode_string(bitref.name)
        )

        bitmap_head_start = coll_header.data_offset + bitref.offset
        (bitdata, bitmap_data) = parse_bitmap_data(
            bitref.size, bitmap_head_start, data
        )

        rows = decode_bitmap(bitdata, bitmap_data, color_table)

        if DEBUG_COLL:
            print(
                f"""---
                {i}: {bitref.name}
        data_size: {len(bitmap_data)}
            width: {bitdata.width}
           height: {bitdata.height}
           pixels: {bitdata.width * bitdata.height}
    bytes_per_row: {bitdata.bytes_per_row}
            flags: {list(bitdata.flags)}
logical_bit_depth: {bitdata.logical_bit_depth}
       width_bits: {bitdata.width_bits}
      height_bits: {bitdata.height_bits}
    pixel_upshift: {bitdata.pixel_upshift}
         encoding: {bitdata.encoding}
             rows: {len(rows) if rows else None}"""
            )
            if rows:
                print('rows 1-10 columns 1-150:')
                render_terminal(rows)
        if rows:
            bitmaps.append((bitref.name, bitdata.width, bitdata.height, rows))
    return bitmaps

def render_terminal(rows):
    for pixels in rows[:20]:
        for (r, g, b, alpha) in pixels[:150]:
            if alpha == 0:
                print(' ', end='')
            else:
                if alpha == 255:
                    char = ' '
                else:
                    char = '.'
                print(f'\x1b[48;2;{r};{g};{b}m{char}\x1b[0m', end='')
        print()

def parse_sequence_bitmaps(data):
    header = myth_headers.parse_header(data)
    coll_header = parse_collection_header(data, header)
    color_table = parse_color_table(data, coll_header)
    bitmap_indices = parse_bitmap_instance(data, coll_header)
    sequences = parse_sequences(data, coll_header)
    bitmaps = parse_bitmaps(data, coll_header, color_table)
    return sequences_to_bitmaps(bitmaps, bitmap_indices, sequences)

def sequences_to_bitmaps(bitmaps, bitmap_indices, sequences):
    bms = []
    for sequence in sequences:
        seq_bms = [
            bitmaps[bitmap_indices[idx]]
            for idx in sequence['instance_indices']
            if bitmap_indices[idx] >= 0 and bitmap_indices[idx] < len(bitmaps)
        ]
        bms.append({
            'name': sequence['name'],
            'bitmaps': seq_bms
        })
    return bms

def parse_collection_header(data, header):
    coll_header = Header256._make(struct.unpack_from(
        Header256Fmt, data, offset=header.tag_data_offset
    ))
    return coll_header._replace(
        data_offset=header.tag_data_offset + coll_header.data_offset
    )

def parse_bitmap_data(total_size, start, data):
    meta_end = start + BITMAP_META_SIZE
    bitmap_data_end = start + total_size

    bitmap_meta = BitmapMeta._make(struct.unpack_from(BitmapMetaFmt, data, offset=start))
    bitmap_meta = bitmap_meta._replace(
        flags=BitmapFlags(bitmap_meta.flags),
        encoding=Encoding(bitmap_meta.encoding)
    )

    if BitmapFlags.NO_ROW_ADDRESS_TABLE in bitmap_meta.flags:
        bitmap_data = data[meta_end:bitmap_data_end]
    else:
        address_table_size = 4 * (bitmap_meta.height - 1)
        address_table_end = meta_end + address_table_size
        bitmap_data = data[address_table_end:bitmap_data_end]

    return (bitmap_meta, bitmap_data)

def decode_bitmap(bitdata, bitmap_data, color_table=None):
    if bitdata.encoding == Encoding.EXT_R8G8B8A5H:
        return decode_bitmap_64(bitmap_data, bitdata.width, bitdata.height)
    elif bitdata.encoding == Encoding.EXT_ARGB_8888_32:
        return decode_bitmap_32(bitmap_data, bitdata.width, bitdata.height)
    if BitmapFlags.TRANSPARENCY_ENCODED_1BIT in bitdata.flags:
        return decode_compressed_bitmap(
            color_table, bitmap_data, bitdata.width, bitdata.height, bitdata.flags
        )
    else:
        return decode_raw_bitmap(color_table, bitmap_data, bitdata.width, bitdata.height)

def decode_raw_bitmap(color_table, bitmap_data, width, height):
    rows = []
    for row_i in range(height):
        row_start = row_i * width
        row_end = row_start + width
        row = []
        for b_ix in bytearray(bitmap_data[row_start:row_end]):
            (r, g, b, _) = color_table[b_ix]
            row.append((r, g, b, 255))
        rows.append(row)
    return rows

# decode_compressed_bitmap:
# 
# for each row in the bitmap
# 
# 000F
# 2 bytes: number of color spans
# 
# 0050
# 2 bytes: number of color pixels
# 
# 003D 0045
# 0047 004B
# 0051 0055
# ...
# 4 bytes: range of color span
#    - 2 byte: span range start
#    - 2 byte: span range end
# These represent the x coord or column in the pixel row for the fully decoded image. x=0:width
# 
# 0C 45 04 AE 00 7E 00 6E 02 67...
# EITHER:
# 1 byte per color pixel: index into the color table
# OR (if the TRANSPARENCY_ENCODED_4BIT flag is set
# 2 byte per color pixel:
#   - 1 byte: encoded alpha value
#   - 1 byte: index into the color table

# e.g. a row of pixels:
# [t c c c t c t t c c] where t = transparent and c = color
# there would be three color spans of 3/1/1 pixels with the following start and ends:
# span 1: start: 1 end: 4
# span 2: start: 5 end: 6
# span 3: start: 8 end: 10
# 
# when iterating over spans, fill the gaps with transparent pixels

def decode_alpha(alpha):
    return (15 - (alpha & 15)) * 17

def decode_compressed_bitmap(color_table, bitmap_data, width, height, flags):
    start = 0
    rows = []
    for row_i in range(height):
        span_start = start + 4
        (num_spans, num_pixels) = struct.unpack_from('>H H', bitmap_data, offset=start)
        if num_spans > width or num_pixels > width:
            print(row_i, num_spans, num_pixels, width)
            return
        spans = []
        for span in utils.iter_unpack(
            span_start, num_spans,
            '>H H', bitmap_data
        ):
            spans.append(span)

        pixel_start = span_start + (num_spans * 4)
        pixel_end = pixel_start
        col_i = 0
        row = []
        total_opaque = 0
        total_transparent = 0
        for (span_range_start, span_range_end) in spans:
            num_preceding_transparent = span_range_start - col_i
            total_transparent += num_preceding_transparent
            row += num_preceding_transparent * [(0,0,0, 0)]

            span_size = span_range_end - span_range_start
            total_opaque += span_size

            for p_i in range(span_size):
                if BitmapFlags.TRANSPARENCY_ENCODED_4BIT in flags:
                    # In 4bit transparency, pixel data is stored as a two byte sequence:
                    # alpha, index
                    pixel_end = pixel_start + 2
                    (alpha, ct_idx) = struct.unpack('>B B', bitmap_data[pixel_start:pixel_end])

                    (r, g, b, _) = color_table[ct_idx]
                    row.append((r, g, b, decode_alpha(alpha)))
                else:
                    pixel_end = pixel_start + 1
                    (ct_idx,) = struct.unpack('>B', bitmap_data[pixel_start:pixel_end])

                    (r, g, b, _) = color_table[ct_idx]
                    row.append((r, g, b, 255))
                pixel_start = pixel_end

            col_i = col_i + num_preceding_transparent + span_size

        remaining = (width - col_i)
        total_transparent += remaining
        row += remaining * [(0,0,0, 0)]

        rows.append(row)

        if BitmapFlags.WORD_ALIGNED_ENCODING in flags:
            pixel_end = word_align(pixel_end)
        start = pixel_end

    return rows

A5H3PIXEL_A_MASK = 0x1f
def a5h3pixel(a, h):
    return a | (h << 5)
def a5h3pixel_a(v):
    return v & A5H3PIXEL_A_MASK
def a5h3pixel_h(v):
    return v >> 5

def a5h3_pixel_a_int(v):
    return round(255 * a5h3pixel_a(v) / A5H3PIXEL_A_MASK)

def is_transparent_or_opaque(s):
    return ((a5h3pixel_a(s) + 1) & A5H3PIXEL_A_MASK) <= 1
def is_opaque(s):
    return a5h3pixel_a(s) == A5H3PIXEL_A_MASK

def decode_bitmap_32(bitmap_data, width, height):
    pixel_count = width * height
    pixels = []
    for (b, g, r, a) in utils.iter_unpack(
        0, pixel_count,
        ">B B B B", bitmap_data
    ):
        pixels.append((r, g, b, a))
    
    rows = []
    pix_i = 0
    for row_i in range(height):
        row = []
        for col_i in range(width):
            pixel = pixels[pix_i]
            row.append(pixel)
            pix_i += 1
        rows.append(row)
    return rows

def decode_pix_64(alpha_state, bitmap_data, byte_index):
    pix = {
        'a': a5h3_pixel_a_int(alpha_state),
        'b': bitmap_data[byte_index],
        'g': bitmap_data[byte_index+1],
        'r': bitmap_data[byte_index+2],
    }
    byte_index += 3
    if pix['b'] & 1:
        pix['b2'] = bitmap_data[byte_index]
        pix['g2'] = bitmap_data[byte_index+1]
        pix['r2'] = bitmap_data[byte_index+2]
        pix['a2'] = a5h3_pixel_a_int(bitmap_data[byte_index+3])
        byte_index += 4
    return (pix, byte_index)

def decode_bitmap_64(bitmap_data, width, height):
    pixels = []
    pixel_count = width * height

    alpha_state = 0
    byte_index = 0
    pixel_length = 0
    while pixel_length < pixel_count:
        if is_transparent_or_opaque(alpha_state):
            # Decode RLE
            run_length = bitmap_data[byte_index]
            byte_index += 1
            for i in range(run_length):
                if is_opaque(alpha_state):
                    (pix, byte_index) = decode_pix_64(alpha_state, bitmap_data, byte_index)
                else:
                    pix = {'a': a5h3pixel_a(alpha_state), 'r': 0, 'g': 0, 'b': 0}
                pixels.append(pix)
            pixel_length += run_length
            alpha_state = a5h3pixel(1, 0)
        else:
            # // Decode Plain
            alpha_state = bitmap_data[byte_index]
            byte_index += 1
            if a5h3pixel_a(alpha_state):
                (pix, byte_index) = decode_pix_64(alpha_state, bitmap_data, byte_index)
            else:
                pix = {'a': a5h3pixel_a(alpha_state), 'r': 0, 'g': 0, 'b': 0}
            pixels.append(pix)
            pixel_length += 1

    rows = []
    pix_i = 0
    for row_i in range(height):
        row = []
        for col_i in range(width):
            pixel = pixels[pix_i]
            row.append((pixel['r'], pixel['g'], pixel['b'], pixel['a']))
            pix_i += 1
        rows.append(row)
    return rows

def parse_hue_change(values):
    hue_change = HueChange._make(values)
    return hue_change._replace(
        name=myth_headers.decode_string(hue_change.name),
        hue0=round(hue_change.hue0 / ANGLE_SF),
        hue1=round(hue_change.hue1 / ANGLE_SF),
        colors_effected=struct.unpack(">32B", hue_change.colors_effected),
        minimum_saturation=round(hue_change.minimum_saturation / FIXED_SF),
        median_hue=round(hue_change.median_hue / ANGLE_SF),
    )

def parse_d256_ref(values):
    ref = D256Ref._make(values)
    return ref._replace(
        name=myth_headers.decode_string(ref.name),
        flags=D256RefFlags(ref.flags)
    )

def parse_d256_header(data, tag_header):
    head_start = tag_header.tag_data_offset
    head_end = head_start + D256HeadSize
    return D256Head._make(struct.unpack(D256HeadFmt, data[head_start:head_end]))

def parse_d256_bitmaps(data, head):
    head_end = myth_headers.TAG_HEADER_SIZE + D256HeadSize
    total_ref_start = head_end + head.ref_offset
    total_ref_end = total_ref_start + head.ref_size
    total_ref_data = data[total_ref_start:total_ref_end]

    ret = []
    for values in utils.iter_unpack(
        0, head.ref_count,
        D256RefFmt, total_ref_data
    ):
        ref = parse_d256_ref(values)
        if DEBUG_COLL:
            print(f'{ref.name:<64} {ref.width:>3}x{ref.height:<3} orig={ref.original_width:>2}x{ref.original_height:<2} {ref.flags}')
        bitmap_meta_start = head_end + ref.offset
        (bitmap_meta, bitmap_data) = parse_bitmap_data(ref.size, bitmap_meta_start, data)
        rows = decode_bitmap(bitmap_meta, bitmap_data)
        if DEBUG_COLL:
            print(bitmap_meta, 'datalen:', len(bitmap_data))
            render_terminal(rows)

        ret.append((ref.name, bitmap_meta.width, bitmap_meta.height, rows))
    return ret

def parse_d256_hues(data, head):
    head_end = myth_headers.TAG_HEADER_SIZE + D256HeadSize

    total_hue_start = head_end + head.hue_changes_offset
    total_hue_end = total_hue_start + head.hue_changes_size
    total_hue_data = data[total_hue_start:total_hue_end]

    hues = []
    for values in utils.iter_unpack(
        0, head.hue_change_count,
        HueChangeFmt, total_hue_data
    ):
        hue_change = parse_hue_change(values)
        hues.append(hue_change)
        if DEBUG_COLL:
            print(
                f'{hue_change.name:<64} '
                f'  0={hue_change.hue0:<3} 1={hue_change.hue1:<3} '
                f'median={hue_change.median_hue:<3} min_sat={hue_change.minimum_saturation:<3}'
            )
            print(hue_change.colors_effected)
    return hues

def parse_d256(data):
    tag_header = myth_headers.parse_header(data)
    head = parse_d256_header(data, tag_header)
    parse_d256_bitmaps(data, head)
    parse_d256_hues(data, head)
