#!/usr/bin/env python3
import sys
import os
import pathlib
import struct

import myth_headers
import font_tag
import tag2png
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(tag_path, text):
    """
    Parse a Myth II font tag file and output the bitmaps
    """
    data = utils.load_file(tag_path)

    header = myth_headers.parse_header(data)
    (width, height, pixel_rows) = parse_font_tag(data, text)

    png = tag2png.make_png(width, height, pixel_rows)
    output_path = pathlib.Path(sys.path[0], f'../output/fonts/font-{header.tag_id}.png').resolve()

    if prompt(output_path):
        pathlib.Path(output_path.parent).mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as png_file:
            png_file.write(png)

def prompt(prompt_path, prefix=''):
    # return False
    response = input(f"{prefix}Write file to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def parse_font_tag(data, text):
    try:
        return font_tag.parse_font_tag(data, text)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <input_file> [<text>]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    text = None
    if len(sys.argv) > 2:
        text = sys.argv[2]

    try:
        main(input_file, text)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
