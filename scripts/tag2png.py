#!/usr/bin/env python3
import sys
import os
import pathlib
import struct
import signal
import enum
import zlib
from collections import namedtuple

import myth_headers

BITMAP_META_SIZE = 48
PNG_HEAD = b'\x89PNG\r\n\x1a\n'

DEBUG = (os.environ.get('DEBUG') == '1')
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

Header256Size = 320
Header256Fmt = """>
    I I
    28H

    I I I I
    I I I I
    I I I I
    I I I I
    I I I I
    I I I I
    I I I I
    I I I I
    
    I I
    24H
    I I I I
    20H
    16c
"""
Header256 = namedtuple("Header256", [
    'flags',
    'user_data',
    *[f'unused_{i}' for i in range(1,29)],
    'color_table_count', 'color_tables_offset', 'color_tables_size', 'color_tables',
    'hue_change_count', 'hue_changes_offset', 'hue_changes_size', 'hue_changes',
    'bitmap_reference_count', 'bitmap_references_offset', 'bitmap_references_size', 'bitmap_references',
    'bitmap_instance_count', 'bitmap_instances_offset', 'bitmap_instances_size', 'bitmap_instances',
    'sequence_reference_count', 'sequence_references_offset', 'sequence_references_size', 'sequence_references',
    'shadow_map_count', 'shadow_maps_offset', 'shadow_maps_size', 'shadow_maps',
    'blend_table_count', 'blend_tables_offset', 'blend_tables_size', 'blend_tables',
    'remapping_table_count', 'remapping_tables_offset', 'remapping_tables_size', 'remapping_tables',
    'shading_table_count', 'shading_table_pointers',
    *[f'unused_{i}' for i in range(29,53)],
    'data_offset', 'data_size', 'data_delta', 'data',
    *[f'unused_{i}' for i in range(53,73)],
    *[f'extractor_{i}' for i in range(1,17)],
])

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

def main(tag_path, png_path):
    """
    Parse a Myth TFL or Myth II .256 tag file and output a PNG file
    """
    data = myth_headers.load_file(tag_path)

    (game_version, tag_id, bitmaps) = parse_256_tag(data)

    if not png_path:
        png_path = f'./png/{game_version}-{tag_id}.png'

    path = pathlib.Path(png_path).with_suffix('.png')

    bitmap_count = len(bitmaps)

    if prompt(path, bitmap_count):
        for i, (width, height, rows) in enumerate(bitmaps):
            png = make_png(width, height, rows)
            
            bitmap_path = path
            if (bitmap_count > 1):
                bitmap_path = path.with_stem(f'{path.stem}-{i}')

            pathlib.Path(bitmap_path.parent).mkdir(parents=True, exist_ok=True)
            with open(bitmap_path, 'wb') as png_file:
                png_file.write(png)
                print(f"PNG extracted. Output saved to {bitmap_path} ({width} x {height})")

def prompt(prompt_path, bitmap_count):
    # return True
    prefix = ''
    suffix = ''
    if (bitmap_count > 1):
        prompt_path = prompt_path.with_stem(f'{prompt_path.stem}-n')
        prefix = f'{bitmap_count}x bitmaps '
        suffix = ' (n=bitmap)'
    response = input(f"Write {prefix}to: {prompt_path}{suffix} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def parse_256_tag(data):
    try:
        header = myth_headers.parse_header(data)

        coll_header = parse_collection_header(data, header)
        color_table = parse_color_table(data, coll_header)
        # parse_bitmap_instance(data, coll_header)
        # parse_sequences(data, coll_header)
        bitmaps = parse_bitmaps(data, coll_header, color_table)

        return (header.tag_version, header.tag_id, bitmaps)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_collection_header(data, header):
    coll_header = Header256._make(struct.unpack(
        Header256Fmt, data[header.tag_data_offset:header.tag_data_offset+Header256Size]
    ))
    return coll_header._replace(
        data_offset=header.tag_data_offset + coll_header.data_offset
    )

def parse_color_table(data, coll_header):
    color_table_start = coll_header.data_offset + coll_header.color_tables_offset
    color_table_end = color_table_start + coll_header.color_tables_size
    color_table_data = data[color_table_start:color_table_end]
    (ct_count, ct_unused) = struct.unpack('>I 28s', color_table_data[:32])
    
    if DEBUG:
        print(f'color table {ct_count}')
    
    color_table = []
    for cc in range(ct_count):
        cc_start = 32 + (cc * 8)
        cc_end = cc_start + 8
        (r, _, g, _, b, _, cc_flags) = struct.unpack('>B c B c B c H', color_table_data[cc_start:cc_end])
        color_table.append((r, g, b, cc_flags))
        if DEBUG:
            print(f'\x1b[48;2;{r};{g};{b}m  \x1b[0m', end='')
            if ((cc % 25) == 24):
                print()
    if DEBUG:
        # print(color_table)
        print('\n')
    return color_table

def parse_bitmap_instance(data, coll_header):
    bitmap_instance_each_size = (
        coll_header.bitmap_instances_size // coll_header.bitmap_instance_count
    )
    bitmap_indices = []
    for c in range(coll_header.bitmap_instance_count):
        bitmap_instance_start = (
            coll_header.data_offset + coll_header.bitmap_instances_offset
            + (c * bitmap_instance_each_size)
        )

        bitmap_instance_end = bitmap_instance_start + bitmap_instance_each_size
        bitmap_instance_data = data[bitmap_instance_start:bitmap_instance_end]

        (bitmap_index, ) = struct.unpack(">h", bitmap_instance_data[28:30])
        bitmap_indices.append(bitmap_index)
        if DEBUG:
            print(
                f'bitmap_instance: {c} {bitmap_instance_data.hex()}'
            )
    return bitmap_indices

def parse_sequences(data, coll_header):
    sequence_reference_each_size = (
        coll_header.sequence_references_size // coll_header.sequence_reference_count
    )
    sequences = []
    for c in range(coll_header.sequence_reference_count):
        sequence_reference_start = (
            coll_header.data_offset + coll_header.sequence_references_offset
            + (c * sequence_reference_each_size)
        )

        sequence_reference_end = sequence_reference_start + sequence_reference_each_size
        sequence_data = data[sequence_reference_start:sequence_reference_end]
        (seq_name, seq_offset, seq_size, seq_unused) = struct.unpack('>64s I I 56s', sequence_data)
        seq_start = coll_header.data_offset + seq_offset
        seq_end = seq_start + seq_size
        seq_data = data[seq_start:seq_end]

        (num_frames,) = struct.unpack(">H", seq_data[10:12])
        frame_instances = seq_data[64:]
        frame_start = 0
        frame_size = 48
        instances_indices = []
        for f in range(num_frames):
            frame_end = frame_start + frame_size
            (index, ) = struct.unpack(">H", frame_instances[frame_start:frame_end][46:])
            instances_indices.append(index)

            frame_start = frame_end

        name = myth_headers.decode_string(seq_name)
        if DEBUG:
            print(
                f'{c} sequence_reference: {name: <32} unused={seq_unused.hex()}'
            )
        sequences.append({
            'name': name,
            'instance_indices': instances_indices
        })

    return sequences

def parse_bitmaps(data, coll_header, color_table):
    bitmaps = []
    bitmap_reference_each_size = (
        coll_header.bitmap_references_size // coll_header.bitmap_reference_count
    )
    for c in range(coll_header.bitmap_reference_count):
        bitmap_reference_start = (
            coll_header.data_offset + coll_header.bitmap_references_offset
            + (c * bitmap_reference_each_size)
        )

        bitmap_reference_end = bitmap_reference_start + bitmap_reference_each_size
        bitref_data = data[bitmap_reference_start:bitmap_reference_end]
        (
            bitref_name,
            bitref_offset, bitref_size,
            bitref_data_1, bitref_data_2,
            bitref_width, bitref_height,
            bitref_unused,
            bitref_extractor
        ) = struct.unpack('>64s I I H H H H 32s 16s', bitref_data)

        bitmap_head_start = coll_header.data_offset + bitref_offset
        bitmap_head_end = bitmap_head_start + BITMAP_META_SIZE
        bitmap_head = data[bitmap_head_start:bitmap_head_end]
        (
            bitdata_width, bitdata_height,
            bitdata_bytes_per_row,
            bitdata_flags,
            bitdata_logical_bit_depth,
            bitdata_width_bits, bitdata_height_bits,
            bitdata_pixel_upshift,
            bitdata_encoding,
            bitdata_unused,
            bitdata_unknown1,
            bitdata_unknown2,
            bitdata_unknown3,
            bitdata_unknown4,
            bitdata_unused2
        ) = struct.unpack('>H H h H H H H H H 10s H H H H 12s', bitmap_head)

        bitmap_flags = BitmapFlags(bitdata_flags)

        bitmap_address_table_start = bitmap_head_end
        bitmap_address_table_size = 4 * bitdata_height
        bitmap_address_table_end = bitmap_address_table_start + bitmap_address_table_size
        # bitmap_address_table = data[bitmap_address_table_start:bitmap_address_table_end]
        # print(bitmap_address_table.hex())
        
        bitmap_data_start = bitmap_address_table_end
        bitmap_data_size = bitref_size - bitmap_address_table_size - BITMAP_META_SIZE
        bitmap_data_end = bitmap_data_start + bitmap_data_size
        bitmap_data = data[bitmap_data_start:bitmap_data_end]

        if DEBUG:
            print(
                f"""{c}: {myth_headers.decode_string(bitref_name)}
       data_start: {bitmap_data_start}
        data_size: {bitmap_data_size}

            width: {bitdata_width}
           height: {bitdata_height}
           pixels: {bitdata_width * bitdata_height}
    bytes_per_row: {bitdata_bytes_per_row}
  
            flags: {list(bitmap_flags)}
logical_bit_depth: {bitdata_logical_bit_depth}
       width_bits: {bitdata_width_bits}
      height_bits: {bitdata_height_bits}
    pixel_upshift: {bitdata_pixel_upshift}
         encoding: {bitdata_encoding}

         unknown1: {bitdata_unknown1}
         unknown2: {bitdata_unknown2}
         unknown3: {bitdata_unknown3}
         unknown4: {bitdata_unknown4}

         rows 1-10 columns 1-150:"""
            )
        if BitmapFlags.TRANSPARENCY_ENCODED_1BIT in bitmap_flags:
            rows = decode_compressed_bitmap(color_table, bitmap_data, bitdata_width, bitdata_height, bitmap_flags)
        else:
            rows = decode_bitmap(color_table, bitmap_data, bitdata_width, bitdata_height)

        if rows:
            if DEBUG:
                render_terminal(rows)

            bitmaps.append((bitdata_width, bitdata_height, rows))
    return bitmaps

def decode_bitmap(color_table, bitmap_data, width, height):
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
        (num_spans, num_pixels) = struct.unpack('>H H', bitmap_data[start:span_start])
        if num_spans > width or num_pixels > width:
            return
        spans = []
        for span_i in range(num_spans):
            span_end = span_start + 4
            span = struct.unpack(
                '>H H', bitmap_data[span_start:span_end]
            )
            spans.append(span)

            span_start = span_end

        pixel_start = span_end
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

        start = pixel_end

    return rows

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

# PNG
# https://www.da.vidbuchanan.co.uk/blog/hello-png.html

def make_png(width, height, pixel_rows):
    return (
        PNG_HEAD
        + png_chunk(b"IHDR", png_header(width, height))
        + png_chunk(b"IDAT", png_data(pixel_rows))
        + png_chunk(b"IEND")
    )

def png_header(width, height):
    return (
        png_u31(width) +
        png_u31(height) +
        bytes([
            8, # bit_depth / 8 bit per channel = 32 bits for r,g,b,a
            6, # color_type / RGBA
            0, # compression_method / zlib/DEFLATE
            0, # filter_method / "adaptive filtering"
            0, # interlace_method / none
        ])
    )

def png_data(pixel_rows):
    filtered = []
    for row in pixel_rows:
        filtered.append(0)
        for (r, g, b, alpha) in row:
            filtered += [r, g, b, alpha]
    return zlib.compress(bytes(filtered), level=9) # level 9 is maximum compression!

def png_chunk(type, data=b''):
    length = len(data)
    crc = zlib.crc32(type + data)
    return (
        png_u31(length) +
        type +
        data +
        png_u31(crc)
    )

def png_u31(value):
    return value.to_bytes(4, "big")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tag2png.py <input_file> [<output_file>]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if len(sys.argv) == 3:
        output_file = sys.argv[2]
    else:
        output_file = None
    
    try:
        main(input_file, output_file)
    except KeyboardInterrupt:
        sys.exit(130)
