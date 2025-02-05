#!/usr/bin/env python3
import signal
import sys
import struct
import pathlib

import myth_headers

DEBUG = False

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def main(mono_path, tag_type, tag_id, output_file):
    """
    Parse a Myth TFL or Myth II monolith file and export provided tag.
    If no tag provided, list all tags
    """
    try:
        with open(mono_path, 'rb') as infile:
            data = infile.read()
    except FileNotFoundError:
        print(f"Error: File not found - {mono_path}")
        sys.exit(1)

    try:
        data_size = len(data)

        (
            header, header_size,
            pre_tag_count, pre_tag_list_start, pre_tag_size,
            tag_count, tag_list_start, tag_list_size
        ) = myth_headers.parse_mono_header(data)

        if DEBUG:
            print('total file length', data_size)
            print('      header size', header_size)
            if pre_tag_count:
                print('    pre tag start', pre_tag_list_start)
                print('    pre tag count', pre_tag_count)
                print('     pre tag size', pre_tag_size)
            print('   tag list start', tag_list_start)
            print('        tag count', tag_count)
            print('    tag list size', tag_list_size)

        if pre_tag_count:
            print(
                """
Pre tags
------+----------------------------------+------------------------------------------------------------------+
 id   | name                             | long
------+----------------------------------+------------------------------------------------------------------+"""
            )
        for i in range(pre_tag_count):
            start = pre_tag_list_start + (i * myth_headers.PRE_TAG_HEADER_SIZE)
            end = start + myth_headers.PRE_TAG_HEADER_SIZE
            pre_tag_header_data = data[start:end]
            (p_tag_id, p_tag_name, p_tag_long_name) = struct.unpack('>16s 32s 64s', pre_tag_header_data)
            p_tag_id = p_tag_id.split(b'\0', 1)[0].decode('mac-roman')
            p_tag_name = p_tag_name.split(b'\0', 1)[0].decode('mac-roman')
            p_tag_long_name = p_tag_long_name.split(b'\0', 1)[0].decode('mac-roman')
            print(f' {p_tag_id: <4} | {p_tag_name: <32} | {p_tag_long_name: <64}')

        print(
            """
Tags
-----+------+------+------+-------
 idx | game | type | id   | name 
-----+------+------+------+-------"""
        )
        for i in range(tag_count):
            start = tag_list_start + (i * myth_headers.TAG_HEADER_SIZE)
            end = start + myth_headers.TAG_HEADER_SIZE
            tag_header_data = data[start:end]
            tag_header = myth_headers.parse_header(tag_header_data)
            if (
                (not tag_id and not tag_type)
                or (tag_type == tag_header.tag_type and tag_id == tag_header.tag_id)
            ):
                print(
                    f' {i:03} | '
                    f'{tag_header.tag_version} | '
                    f'{tag_header.tag_type} | '
                    f'{tag_header.tag_id} | '
                    f'{tag_header.name}'
                )
                if tag_id and tag_type:
                    export_tag(tag_header, data, output_file)

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def export_tag(tag_header, data, output_file):
    tag_start = tag_header.tag_data_offset
    tag_end = tag_start + tag_header.tag_data_size
    tag_data = data[tag_start:tag_end]

    if not output_file:
        output_file = f'./tags/{tag_header.tag_version}-{tag_id}'

    tag_path = pathlib.Path(output_file)

    if prompt(tag_path):
        pathlib.Path(tag_path.parent).mkdir(parents=True, exist_ok=True)
        with open(tag_path, 'wb') as tag_file:
            tag_file.write(myth_headers.encode_header(myth_headers.fix_tag_header_offset(tag_header)))
            tag_file.write(tag_data)
            print(f"Tag extracted. Output saved to {tag_path}")

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mono2tag.py <input_file> [<tag_type> <tag_id> [<output_file>]]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    tag_type = None
    tag_id = None
    output_file = None

    if len(sys.argv) >= 4:
        tag_type = sys.argv[2]
        tag_id = sys.argv[3]
        if len(sys.argv) == 5:
            output_file = sys.argv[4]
    
    try:
        main(input_file, tag_type, tag_id, output_file)
    except KeyboardInterrupt:
        sys.exit(130)
