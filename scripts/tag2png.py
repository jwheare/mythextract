#!/usr/bin/env python3
import sys
import os
import pathlib
import struct
import zlib

import myth_headers
import myth_collection

BITMAP_META_SIZE = 52
PNG_HEAD = b'\x89PNG\r\n\x1a\n'

DEBUG = (os.environ.get('DEBUG') == '1')

def main(tag_path, output_dir):
    """
    Parse a Myth TFL or Myth II .256 tag file and output a PNG file
    """
    data = myth_headers.load_file(tag_path)

    (game_version, tag_id, bitmaps) = parse_256_tag(data)

    if not output_dir:
        output_dir = f'../output/png/{game_version}-{tag_id}'
        path = pathlib.Path(sys.path[0], output_dir).resolve()
    else:
        path = pathlib.Path(output_dir)

    bitmap_count = len(bitmaps)

    if prompt(path, bitmap_count):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        for i, (name, width, height, rows) in enumerate(bitmaps):
            png = make_png(width, height, rows)
            
            bitmap_path = path / f'{i}-{name}.png'
            with open(bitmap_path, 'wb') as png_file:
                png_file.write(png)
                print(f"PNG extracted. Output saved to {bitmap_path} ({width} x {height})")

def prompt(prompt_path, bitmap_count):
    # return True
    response = input(f"Write {bitmap_count}x bitmaps to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def parse_256_tag(data):
    try:
        header = myth_headers.parse_header(data)
        if header.tag_type == '.256':
            coll_header = myth_collection.parse_collection_header(data, header)
            color_table = myth_collection.parse_color_table(data, coll_header)
            # myth_collection.parse_bitmap_instance(data, coll_header)
            # myth_collection.parse_sequences(data, coll_header)
            bitmaps = myth_collection.parse_bitmaps(data, coll_header, color_table)
        elif header.tag_type == 'd256':
            d_header = myth_collection.parse_d256_header(data, header)
            if DEBUG:
                head_d = d_header._asdict()
                for f, val in head_d.items():
                    print(f'{f:<20} {val}')
                print('len', len(data))
                print('header.tag_data_size', header.tag_data_size)
                print(header.tag_data_size - d_header.data_size)

            bitmaps = myth_collection.parse_d256_bitmaps(data, d_header)

        return (header.signature, header.tag_id, bitmaps)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

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
        print("Usage: python3 tag2png.py <input_file> [<output_dir>]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if len(sys.argv) == 3:
        output_dir = sys.argv[2]
    else:
        output_dir = None
    
    try:
        main(input_file, output_dir)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
