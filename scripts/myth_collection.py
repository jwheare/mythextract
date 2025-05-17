#!/usr/bin/env python3
import enum
import os
import struct

import myth_headers
import utils

DEBUG_COLL = (os.environ.get('DEBUG_COLL') == '1')

ANGLE_SF = (0xffff / 360)
FIXED_SF = 1 << 16

ColorFmt = ('Color', [
    ('H', 'r', (FIXED_SF - 1)),
    ('H', 'g', (FIXED_SF - 1)),
    ('H', 'b', (FIXED_SF - 1)),
    ('H', 'flags'),
])

CollectionRefFmt = ('CollectionRef', [
    ('4s', 'collection_tag', utils.decode_string),
    ('H', 'number_of_permutations'),
    ('H', 'tint_fraction'),
    ('320s', 'colors', lambda colors: [utils.list_codec('PermutationHue', 8, ColorFmt)(colors) for i in range(5)]),
    ('8s', 'tint', ColorFmt),
    ('36x', None),
    ('2x', None),
    ('10x', None),
])

D256HeadSize = 64
D256HeadFmt = ('D256Head', [
    ('L', 'flags'),
    ('4s', 'tag_id'),
    ('L', 'ref_count'),
    ('L', 'ref_offset'),
    ('L', 'ref_size'),
    ('20x', None),
    ('L', 'data_offset'),
    ('L', 'data_size'),
    ('L', 'data_delta'),
    ('L', 'hue_change_count'),
    ('L', 'hue_changes_offset'),
    ('L', 'hue_changes_size'),
])

class D256RefFlags(enum.Flag):
    UNMIRROR = enum.auto()

D256RefFmt = ('D256Ref', [
    ('64s', 'name', utils.decode_string),
    ('L', 'offset'),
    ('L', 'size'),
    ('8x', None),
    ('H', 'width'),
    ('H', 'height'),
    ('L', 'original_checksum'),
    ('H', 'original_reference_point_x'),
    ('H', 'original_reference_point_y'),
    ('H', 'detail_reference_point_x'),
    ('H', 'detail_reference_point_y'),
    ('L', 'detail_pixels_to_world'),
    ('H', 'original_width'),
    ('H', 'original_height'),
    ('L', 'flags', D256RefFlags),
    ('20x', None),
])

HueChangeFmt = ('HueChange', [
    ('64s', 'name', utils.decode_string),
    ('H', 'hue0', ANGLE_SF),
    ('H', 'hue1', ANGLE_SF),
    ('32s', 'colors_effected', utils.list_pack('HueChangeColors', 32, '>B')),
    ('H', 'minimum_saturation', FIXED_SF),
    ('H', 'median_hue', ANGLE_SF),
    ('H', 'flags'),
    ('6x', None),
    ('16x', None),
])

Header256Fmt = ("Header256", [
    ('I', 'flags'),
    ('I', 'user_data'),
    ('56x', None),
    ('I', 'color_table_count'),
    ('I', 'color_tables_offset'),
    ('I', 'color_tables_size'),
    ('I', 'color_tables'),
    ('I', 'hue_change_count'),
    ('I', 'hue_changes_offset'),
    ('I', 'hue_changes_size'),
    ('I', 'hue_changes'),
    ('I', 'bitmap_reference_count'),
    ('I', 'bitmap_references_offset'),
    ('I', 'bitmap_references_size'),
    ('I', 'bitmap_references'),
    ('I', 'bitmap_instance_count'),
    ('I', 'bitmap_instances_offset'),
    ('I', 'bitmap_instances_size'),
    ('I', 'bitmap_instances'),
    ('I', 'sequence_reference_count'),
    ('I', 'sequence_references_offset'),
    ('I', 'sequence_references_size'),
    ('I', 'sequence_references'),
    ('I', 'shadow_map_count'),
    ('I', 'shadow_maps_offset'),
    ('I', 'shadow_maps_size'),
    ('I', 'shadow_maps'),
    ('I', 'blend_table_count'),
    ('I', 'blend_tables_offset'),
    ('I', 'blend_tables_size'),
    ('I', 'blend_tables'),
    ('I', 'remapping_table_count'),
    ('I', 'remapping_tables_offset'),
    ('I', 'remapping_tables_size'),
    ('I', 'remapping_tables'),
    ('I', 'shading_table_count'),
    ('I', 'shading_table_pointers'),
    ('48x', None),
    ('I', 'data_offset'),
    ('I', 'data_size'),
    ('I', 'data_delta'),
    ('I', 'data'),
    ('40x', None),
    ('16x', None),
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

BITMAP_META_SIZE = 52
BitmapMetaFmt = ('BitmapMeta', [
    ('H', 'width'),
    ('H', 'height'),
    ('h', 'bytes_per_row'),
    ('H', 'flags', BitmapFlags),
    ('H', 'logical_bit_depth'),
    ('H', 'width_bits'),
    ('H', 'height_bits'),
    ('H', 'pixel_upshift'),
    ('H', 'encoding', Encoding),
    ('34x', None),
])

def parse_collection_ref(data):
    return utils.codec(CollectionRefFmt, offset=64)(data)

def word_align(value):
    return value + (value & 1)

def parse_color_table(data, coll_header):
    color_table_start = coll_header.data_offset + coll_header.color_tables_offset
    color_table_end = color_table_start + coll_header.color_tables_size
    color_table_data = data[color_table_start:color_table_end]
    color_table_head_end = 32
    (ct_count,) = struct.unpack('>I 28x', color_table_data[:color_table_head_end])
    
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

class InstanceFlags(enum.Flag):
    MIRROR_HORIZONTAL = enum.auto()
    MIRROR_VERTICAL = enum.auto()
    TRANSPARENT = enum.auto()
    KEYPOINT_OBSCURED = enum.auto()
    TEXTURE = enum.auto() # this is a texture, not a 1-bit transparency encoded rectangle
    HIGHRES = enum.auto()
    SEQUENCE_MIRRORED = enum.auto()

BitmapInstanceFmt = ('BitmapInstance', [
    ('L', 'flags', InstanceFlags),
    ('8x', None),
    ('H', 'reg_point_x'),
    ('H', 'reg_point_y'),
    ('8x', None),
    ('H', 'key_point_x'),
    ('H', 'key_point_y'),
    ('h', 'bitmap_index'),
    ('H', 'highres_bitmap_index'),
    ('l', 'highres_pixels_to_world'),
    ('H', 'highres_reg_point_x'),
    ('H', 'highres_reg_point_y'),
    ('8x', None),
    ('16x', None),
])

def parse_bitmap_instance(data, coll_header):
    bitmap_instance_start = coll_header.data_offset + coll_header.bitmap_instances_offset
    return utils.list_codec(
        'BitmapInstances',
        coll_header.bitmap_instance_count,
        BitmapInstanceFmt,
        offset=bitmap_instance_start,
    )(data)

SEQ_DATA_SIZE = 64
class SequenceFlags(enum.Flag):
    USES_MIRRORING = enum.auto() # right-facing views are mirrored from left-facing views
    HAS_FRAME_DATA = enum.auto() # sequence has the new-style frame_data structures (always set)
    HAS_NO_ROTATION = enum.auto() # instead of being different rotations of the same shape

SequenceDataFmt = ('SequenceData', [
    ('L', 'flags', SequenceFlags),
    ('l', 'pixels_to_world', FIXED_SF),
    ('h', 'number_of_views'),
    ('h', 'frames_per_view'),
    ('h', 'ticks_per_frame'),
    ('h', 'key_frame'),
    ('h', 'loop_frame'),
    ('h', 'sound_index_first'),
    ('h', 'sound_index_key'),
    ('h', 'sound_index_last'),
    ('4s', 'sound_tag_first'),
    ('4s', 'sound_tag_key'),
    ('4s', 'sound_tag_last'),
    ('h', 'transfer_mode'),
    ('h', 'transfer_period'),
    ('l', 'radius', FIXED_SF),
    ('l', 'height0', FIXED_SF),
    ('l', 'height1', FIXED_SF),
    ('h', 'world_radius'),
    ('h', 'world_height0'),
    ('h', 'world_height1'),
    ('6x', None),
])

SequenceRefFmt = ('SequenceRef', [
    ('64s', 'name', utils.decode_string),
    ('I', 'offset'),
    ('I', 'size'),
    ('56x', None),
])

SequenceFrameFmt = ('SequenceFrame', [
    ('h', 'shadow_map_index'),
    ('H', 'key_point_x'),
    ('H', 'key_point_y'),
    ('H', 'key_point_z'),
    ('38x', None),
])

def parse_sequences(data, coll_header):
    sequences = []
    if coll_header.sequence_reference_count:
        sequence_reference_start = coll_header.data_offset + coll_header.sequence_references_offset
        for i, seq_ref in enumerate(utils.list_codec(
            'SequenceRefs',
            coll_header.sequence_reference_count,
            SequenceRefFmt,
            offset=sequence_reference_start
        )(data)):
            seq_start = coll_header.data_offset + seq_ref.offset
            seq_end = seq_start + SEQ_DATA_SIZE
            seq_data = utils.codec(SequenceDataFmt, offset=seq_start)(data)

            view_length = seq_data.number_of_views * 2
            frames = []

            frame_start = seq_end
            for frame_i in range(seq_data.frames_per_view):
                frame = utils.codec(SequenceFrameFmt, offset=frame_start)(data)
                view_start = frame_start + frame._item_def_size
                views = utils.list_pack('SequenceView', seq_data.number_of_views, '>h', offset=view_start)(data)

                frames.append((frame, views))

                frame_start = view_start + view_length
            if DEBUG_COLL:
                print(
                    f'{i:>2} sequence: {seq_ref.name:<32} '
                    f'frames: {frames}'
                )
            sequences.append({
                'name': seq_ref.name,
                'frames': frames,
                'metadata': seq_data,
            })

    return sequences

BitmapReferenceFmt = ('BitmapReference', [
    ('64s', 'name', utils.decode_string),
    ('I', 'offset'),
    ('I', 'size'),
    ('H', 'data_1'),
    ('H', 'data_2'),
    ('H', 'width'),
    ('H', 'height'),
    ('32x', None),
    ('16x', None),
])

def parse_bitmaps(data, coll_header, color_table):
    bitmaps = []
    bitmap_reference_start = coll_header.data_offset + coll_header.bitmap_references_offset
    for i, bitref in enumerate(utils.iter_decode(
        bitmap_reference_start, coll_header.bitmap_reference_count,
        BitmapReferenceFmt, data
    )):
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

class ShadowMapFlags(enum.Flag):
    IS_LIGHT_MAP = enum.auto() # changes application function
    MIRROR_HORIZONTAL = enum.auto()
    MIRROR_VERTICAL = enum.auto()

ShadowMapFmt = ('ShadowMap', [
    ('L', 'flags', ShadowMapFlags),
    ('l', 'reg_point_x', FIXED_SF * 5),
    ('l', 'reg_point_y', FIXED_SF * 5),
    ('h', 'bitmap_index'),
    ('2x', None),
    ('16x', None),
])

def parse_shadow_maps(data, coll_header):
    shadow_map_start = coll_header.data_offset + coll_header.shadow_maps_offset
    return utils.list_codec(
        'ShadowMaps',
        coll_header.shadow_map_count,
        ShadowMapFmt,
        offset=shadow_map_start,
    )(data)

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
    bitmap_instances = parse_bitmap_instance(data, coll_header)
    sequences = parse_sequences(data, coll_header)
    bitmaps = parse_bitmaps(data, coll_header, color_table)
    return sequences_to_bitmaps(bitmaps, bitmap_instances, sequences)

def sequences_to_bitmaps(bitmaps, bitmap_instances, sequences):
    bms = []
    for sequence in sequences:
        seq_bms = []
        for (frame, views) in sequence['frames']:
            idx = views[0]
            bitmap_index = bitmap_instances[idx].bitmap_index
            if bitmap_index > -1 and bitmap_index < len(bitmaps):
               seq_bms.append(bitmaps[bitmap_index])
        bms.append({
            'name': sequence['name'],
            'bitmaps': seq_bms
        })
    return bms

def parse_collection_header(data, header):
    coll_header = utils.codec(Header256Fmt, offset=header.tag_data_offset)(data)
    return coll_header._replace(
        data_offset=header.tag_data_offset + coll_header.data_offset
    )

def parse_bitmap_data(total_size, start, data):
    meta_end = start + BITMAP_META_SIZE
    bitmap_data_end = start + total_size

    bitmap_meta = utils.codec(BitmapMetaFmt, offset=start)(data)

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

def parse_d256_header(data, tag_header):
    return utils.codec(D256HeadFmt, offset=tag_header.tag_data_offset)(data)

def parse_d256_bitmaps(data, head):
    head_end = myth_headers.TAG_HEADER_SIZE + D256HeadSize
    total_ref_start = head_end + head.ref_offset
    total_ref_end = total_ref_start + head.ref_size
    total_ref_data = data[total_ref_start:total_ref_end]

    ret = []
    for ref in utils.iter_decode(
        0, head.ref_count,
        D256RefFmt, total_ref_data
    ):
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
    for hue_change in utils.iter_decode(
        0, head.hue_change_count,
        HueChangeFmt, total_hue_data
    ):
        hues.append(hue_change)
        if DEBUG_COLL:
            print(
                f'{hue_change.name:<64} '
                f'  0={round(hue_change.hue0):<3} 1={round(hue_change.hue1):<3} '
                f'median={round(hue_change.median_hue):<3} min_sat={round(hue_change.minimum_saturation):<3}'
            )
            print(hue_change.colors_effected)
    return hues

def parse_d256(data):
    tag_header = myth_headers.parse_header(data)
    head = parse_d256_header(data, tag_header)
    parse_d256_bitmaps(data, head)
    parse_d256_hues(data, head)
