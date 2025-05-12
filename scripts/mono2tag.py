#!/usr/bin/env python3
import os
import sys
import struct
import pathlib
import re
from collections import OrderedDict

import myth_headers
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(mono_path, tag_type, tag_id, output_file):
    """
    Parse a Myth TFL or Myth II monolith file and export provided tag.
    If no tag provided, list all tags
    """
    mono_path = pathlib.Path(mono_path)
    data = utils.load_file(mono_path)

    try:
        mono_header = myth_headers.parse_mono_header(mono_path.name, data)

        debug_mono_header(mono_header, data)

        entrypoints = get_entrypoints(data, mono_header)
        if len(entrypoints):
            print_entrypoint_map(entrypoints)

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

def debug_mono_header(mono_header, data):
    if DEBUG:
        print(mono_header)
        print('     game version', mono_header.game_version)
        print('total file length', len(data))
        print('      header size', mono_header.header_size)
        if mono_header.entry_tag_count:
            print('    entry tag start', mono_header.entry_tag_list_start)
            print('    entry tag count', mono_header.entry_tag_count)
            print('     entry tag size', mono_header.entry_tag_count * myth_headers.ENTRY_TAG_HEADER_SIZE)
        print('   tag list start', mono_header.tag_list_start)
        print('        tag count', mono_header.tag_count)
        print('    tag list size', mono_header.tag_list_size)

def get_tags(data, mono_header):
    tags = []
    for i in range(mono_header.tag_count):
        start = mono_header.tag_list_start + (i * myth_headers.TAG_HEADER_SIZE)
        end = start + myth_headers.TAG_HEADER_SIZE
        tag_header_data = data[start:end]
        tags.append((i, myth_headers.parse_header(tag_header_data)))
    return tags

def encode_entrypoints(data, sb_mono_header, entrypoints):
    current_size = sb_mono_header.entry_tag_count * myth_headers.ENTRY_TAG_HEADER_SIZE
    entry_tag_count = 0
    entry_tag_data = b''
    for entry_id, (entry_name, entry_long_name, archive_list) in entrypoints.items():
        entry_id = utils.encode_string(entry_id)
        entry_name = utils.encode_string(entry_name)
        entry_long_name = utils.encode_string(entry_long_name)
        entry_tag_data += struct.pack('>16s 32s 64s', entry_id, entry_name, entry_long_name)
        entry_tag_count += 1
    new_size = entry_tag_count * myth_headers.ENTRY_TAG_HEADER_SIZE
    size_diff = current_size - new_size
    sb_mono_header._replace(
        entry_tag_count=entry_tag_count,
        size=sb_mono_header.size - size_diff
    )
    tag_list_start = myth_headers.SB_MONO_HEADER_SIZE + new_size
    tag_list_data = data[tag_list_start:]
    return myth_headers.encode_sb_mono_header(sb_mono_header) + entry_tag_data + tag_list_data

def get_entrypoints(data, mono_header):
    entrypoints = []
    for (entry_id, entry_name, entry_long_name) in utils.iter_unpack(
        mono_header.header_size,
        mono_header.entry_tag_count,
        '>16s 32s 64s',
        data
    ):
        entry_id = utils.decode_string(entry_id)
        entry_name = utils.decode_string(entry_name)
        entry_long_name = utils.decode_string(entry_long_name)
        entrypoints.append((entry_name, (entry_id, (entry_name, entry_long_name, [mono_header.filename]))))
    return OrderedDict([item for (_, item) in sorted(entrypoints)])

NameColorMap = {
    '0': 245, # White
    '1': 26, # Blue
    '2': 98, # Purple
    '3': 88, # Red
    '4': 2, # Green
    '5': 64, # Yellow Green
    '6': 202, # Orange
    '7': 245, # White
}
def name2color(text):
    """If the name starts with a 3 digit number, apply a color"""
    m = re.search(r'^(\d)\d{2,2}', text)
    if m:
        return NameColorMap.get(m.group(1))

def format_entry_name(long_name, name):
    color = name2color(name)
    text = utils.ansi_format(long_name)
    if color:
        return f'\x1b[38;5;{color}m{text:<64}\x1b[0m'
    return f'{text:<64}'

def print_entrypoint_map(entrypoint_map, suffix=''):
    print(
        f"""
Entrypoints{suffix}
------+------------------------------------------+----------------------------------+------------------------------------------------------------------+
 id   | archive                                  | name                             | printable name
------+------------------------------------------+----------------------------------+------------------------------------------------------------------+"""
    )
    for entry_id, entrypoint in entrypoint_map.items():
        print(entrypoint_entry(entry_id, entrypoint))
    print('---')

def entrypoint_entry(entry_id, entrypoint):
    (entry_name, entry_long_name, archive_list) = entrypoint
    archive_name = ' < '.join(archive_list)
    return (
        f' {entry_id: <4} |'
        f' {archive_name: <40} |'
        f' {entry_name:<32} |'
        f' {format_entry_name(entry_long_name, entry_name)}'
    )

def seek_tag(tags, tag_type, tag_id, data, mono_header):
    for (i, tag_header) in tags:
        if (
            tag_header.tag_type == tag_type and
            tag_header.tag_id == tag_id
        ):
            tag_start = tag_header.tag_data_offset
            tag_end = tag_start + tag_header.tag_data_size
            return myth_headers.encode_header(tag_header) + data[tag_start:tag_end]

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
