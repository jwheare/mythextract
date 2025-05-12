#!/usr/bin/env python3
import sys
import os

import myth_headers
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(tag_path, index):
    """
    Parse a Myth TFL or Myth II stli tag file and output as text
    """
    data = utils.load_file(tag_path)

    try:
        (stli_header, stli_text) = myth_headers.parse_text_tag(data)
        print(f"[{stli_header.tag_id}] {stli_header.name}")
        for i, s in enumerate(stli_text.split(b'\r')):
            if index in [None, i]:
                print(f"{i:>3} {utils.decode_string(s)}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Error processing binary data: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 stli2text.py <input_file> [<index>]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if len(sys.argv) == 3:
        index = int(sys.argv[2])
    else:
        index = None
    
    try:
        main(input_file, index)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
