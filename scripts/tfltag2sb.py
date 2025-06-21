#!/usr/bin/env python3
import os
import pathlib
import struct
import sys

import myth_headers
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(input_file):
    """
    Prints header info for an extracted tag file
    """
    tag_data = utils.load_file(input_file)
    try:
        convert_tag(tag_data)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def convert_tag(tag_data):
    tag_header = myth_headers.parse_header(tag_data)
    print(tag_header)
    output_dir = '../output/tfltag2sb/local'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    sb_tag_data = myth_headers.tfl2sb(tag_header, tag_data[myth_headers.TAG_HEADER_SIZE:])

    file_path = (output_path / f'{utils.local_folder(tag_header)}/{tag_header.name}')
    pathlib.Path(file_path.parent).mkdir(parents=True, exist_ok=True)

    with open(file_path, 'wb') as tag_file:
        tag_file.write(sb_tag_data)

    print(f"Tag converted. Output saved to {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tfltag2sb.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]

    try:
        main(input_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
