#!/usr/bin/env python3
import os
import sys
import struct
import pathlib
import hashlib

import myth_headers
import mono2tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(file_1, file_2):
    """
    Parse two plugin files and print the differences
    """
    path_1 = pathlib.Path(file_1)
    data_1 = myth_headers.load_file(path_1)
    path_2 = pathlib.Path(file_2)
    data_2 = myth_headers.load_file(path_2)

    try:
        mono_header_1 = myth_headers.parse_mono_header(path_1.name, data_1)
        mono_header_2 = myth_headers.parse_mono_header(path_2.name, data_2)

        (game_version_1, tags_1, entrypoint_map_1, data_map_1) = loadtags.build_tag_map([(
            (0, 1),
            path_1.name,
            path_1.parent,
            path_1,
            mono_header_1
        )])
        (game_version_2, tags_2, entrypoint_map_2, data_map_2) = loadtags.build_tag_map([(
            (0, 2),
            path_2.name,
            path_2.parent,
            path_2,
            mono_header_2
        )])

        diff_mono_headers(mono_header_1, mono_header_2)

        diff_entrypoints(entrypoint_map_1, entrypoint_map_2)

        diff_tags(tags_1, tags_2, data_map_1, data_map_2)

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def print_tag(side, tag_header, data):
    data_hash = hashlib.md5(data).hexdigest()[:5]
    print(
        f'  {side}  | '
        f'{tag_header.signature} | '
        f'{tag_header.tag_type} | '
        f'{tag_header.tag_id} | '
        f'{data_hash} | '
        f'{tag_header.name}'
    )

def diff_entrypoints(entrypoint_map_1, entrypoint_map_2):
    if len(entrypoint_map_1) or len(entrypoint_map_2):
        print(
            """
Entrypoints
-----+------+------------------------------------------+----------------------------------+------------------------------------------------------------------+
 dif | id   | archive                                  | name                             | printable name
-----+------+------------------------------------------+----------------------------------+------------------------------------------------------------------+"""
        )
    for entry_id_1, entrypoint_1 in entrypoint_map_1.items():
        entry_1 = mono2tag.entrypoint_entry(entry_id_1, entrypoint_1)
        if entry_id_1 not in entrypoint_map_2:
            print(f'  <  |{entry_1}')
        else:
            entrypoint_2 = entrypoint_map_2[entry_id_1]
            entry_2 = mono2tag.entrypoint_entry(entry_id_1, entrypoint_2)

            (entry_name_1, entry_long_name_1, _) = entrypoint_1
            (entry_name_2, entry_long_name_2, _) = entrypoint_2

            if (
                (entry_name_1 != entry_name_2) or
                (entry_long_name_1 != entry_long_name_2)
            ):
                print(f'  <  |{entry_1}')
                print(f'  >  |{entry_2}')
    for entry_id_2, entrypoint_2 in entrypoint_map_2.items():
        entry_2 = mono2tag.entrypoint_entry(entry_id_2, entrypoint_2)
        if entry_id_2 not in entrypoint_map_1:
            print(f'  >  |{entry_2}')
    print('---')

def diff_tags(tags_1, tags_2, data_map_1, data_map_2):
    print(
        """
Tags
-----+------+------+------+-------+-------
 dif | game | type | id   | hash  | name  
-----+------+------+------+-------+-------"""
    )
    for tag_type_1, tag_ids_1 in tags_1.items():
        for tag_id_1, headers_1 in tag_ids_1.items():
            (location_1, tag_header_1, tag_data_1) = loadtags.get_tag_info(tags_1, data_map_1, tag_type_1, tag_id_1)
            if tag_type_1 not in tags_2:
                # tag types in 1 but not 2
                print_tag('<', tag_header_1, tag_data_1)
            elif tag_id_1 not in tags_2[tag_type_1]:
                # tag id in 1 but not 2
                print_tag('<', tag_header_1, tag_data_1)
            else:
                # data mismatch
                (location_2, tag_header_2, tag_data_2) = loadtags.get_tag_info(tags_2, data_map_2, tag_type_1, tag_id_1)
                if tag_data_1 != tag_data_2:
                    print_tag('<', tag_header_1, tag_data_1)
                    print_tag('>', tag_header_2, tag_data_2)
    for tag_type_2, tag_ids_2 in tags_2.items():
        for tag_id_2, headers_2 in tag_ids_2.items():
            (location_2, tag_header_2, tag_data_2) = loadtags.get_tag_info(tags_2, data_map_2, tag_type_2, tag_id_2)
            if tag_type_2 not in tags_1:
                # tag types in 2 but not 1
                print_tag('>', tag_header_2, tag_data_2)
            elif tag_id_2 not in tags_1[tag_type_2]:
                # tag id in 2 but not 1
                print_tag('>', tag_header_2, tag_data_2)

def diff_mono_headers(mono_header_1, mono_header_2):
    print(mono_header_1)
    print(mono_header_2)
    print('     game version', mono_header_1.game_version, mono_header_2.game_version)
    print('  entry tag count', mono_header_1.entry_tag_count, mono_header_2.entry_tag_count)
    print('        tag count', mono_header_1.tag_count, mono_header_2.tag_count)
    print('    tag list size', mono_header_1.tag_list_size, mono_header_2.tag_list_size)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 mono2tag.py <file_1> <file_2>")
        sys.exit(1)
    
    file_1 = sys.argv[1]
    file_2 = sys.argv[2]
    
    try:
        main(file_1, file_2)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
