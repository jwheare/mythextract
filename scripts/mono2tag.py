#!/usr/bin/env python3
import os
import sys
import struct
import pathlib
from collections import OrderedDict

import myth_headers

DEBUG = (os.environ.get('DEBUG') == '1')

def main(mono_path, tag_type, tag_id, output_file):
    """
    Parse a Myth TFL or Myth II monolith file and export provided tag.
    If no tag provided, list all tags
    """
    data = myth_headers.load_file(mono_path)

    try:
        data_size = len(data)

        mono_header = myth_headers.parse_mono_header(data)

        if DEBUG:
            print(mono_header)
            print('     game version', mono_header.game_version)
            print('total file length', data_size)
            print('      header size', mono_header.header_size)
            if mono_header.entry_tag_count:
                print('    entry tag start', mono_header.entry_tag_list_start)
                print('    entry tag count', mono_header.entry_tag_count)
                print('     entry tag size', mono_header.entry_tag_count * myth_headers.ENTRY_TAG_HEADER_SIZE)
            print('   tag list start', mono_header.tag_list_start)
            print('        tag count', mono_header.tag_count)
            print('    tag list size', mono_header.tag_list_size)

        entrypoints = get_entrypoints(data, mono_header)
        if len(entrypoints):
            print_entrypoints(entrypoints, mono_header.name)

        print(
            """
Tags
-----+------+------+------+-------
 idx | game | type | id   | name 
-----+------+------+------+-------"""
        )
        for (i, tag_header) in get_tags(data, mono_header):
            if (
                (not tag_id and not tag_type)
                or (tag_type == tag_header.tag_type and tag_id == tag_header.tag_id)
            ):
                print(
                    f' {i:03} | '
                    f'{tag_header.signature} | '
                    f'{tag_header.tag_type} | '
                    f'{tag_header.tag_id} | '
                    f'{tag_header.name}'
                )
                if tag_id and tag_type:
                    export_tag(tag_header, data, output_file)
                    return

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def get_tags(data, mono_header):
    for i in range(mono_header.tag_count):
        start = mono_header.tag_list_start + (i * myth_headers.TAG_HEADER_SIZE)
        end = start + myth_headers.TAG_HEADER_SIZE
        tag_header_data = data[start:end]
        yield (i, myth_headers.parse_header(tag_header_data))

def get_entrypoints(data, mono_header):
    entrypoints = []
    for i in range(mono_header.entry_tag_count):
        start = mono_header.header_size + (i * myth_headers.ENTRY_TAG_HEADER_SIZE)
        end = start + myth_headers.ENTRY_TAG_HEADER_SIZE
        entry_tag_header_data = data[start:end]
        (entry_id, entry_name, entry_long_name) = struct.unpack('>16s 32s 64s', entry_tag_header_data)
        entry_id = myth_headers.decode_string(entry_id)
        entry_name = myth_headers.decode_string(entry_name)
        entry_long_name = myth_headers.decode_string(entry_long_name)
        entrypoints.append((entry_name, (entry_id, (entry_name, entry_long_name))))
    return OrderedDict([item for (_, item) in sorted(entrypoints)])

def print_entrypoint_map(entrypoint_map):
    for header_name, entrypoints in entrypoint_map.items():
        print_entrypoints(entrypoints, header_name)

def print_entrypoints(entrypoints, header_name):
    print(
        f"""
Entrypoints: {header_name}
------+----------------------------------+------------------------------------------------------------------+
 id   | name                             | long
------+----------------------------------+------------------------------------------------------------------+"""
    )
    for entry_id, (entry_name, entry_long_name) in entrypoints.items():
        print(f' {entry_id: <4} | {entry_name: <32} | {entry_long_name: <64}')
    print('---')

def seek_tag_data(data, tag_type, tag_id):
    mono_header = myth_headers.parse_mono_header(data)

    for i in range(mono_header.tag_count):
        start = mono_header.tag_list_start + (i * myth_headers.TAG_HEADER_SIZE)
        end = start + myth_headers.TAG_HEADER_SIZE
        tag_header_data = data[start:end]
        tag_header = myth_headers.parse_header(tag_header_data)
        if tag_type == tag_header.tag_type and tag_id == tag_header.tag_id:
            tag_start = tag_header.tag_data_offset
            tag_end = tag_start + tag_header.tag_data_size
            tag_data = data[tag_start:tag_end]
            return (
                myth_headers.encode_header(tag_header)
                + tag_data
            )

def export_tag(tag_header, data, output_file):
    tag_start = tag_header.tag_data_offset
    tag_end = tag_start + tag_header.tag_data_size
    tag_data = data[tag_start:tag_end]

    if not output_file:
        output_file = f'../tags/{tag_header.signature}-{tag_header.tag_type}-{tag_id}'
        tag_path = pathlib.Path(sys.path[0], output_file).resolve()
    else:
        tag_path = pathlib.Path(output_file)

    if prompt(tag_path):
        pathlib.Path(tag_path.parent).mkdir(parents=True, exist_ok=True)
        with open(tag_path, 'wb') as tag_file:
            tag_file.write(myth_headers.encode_header(tag_header))
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
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
