#!/usr/bin/env python3
import sys
import os
import struct

import myth_headers
import myth_collection
import mons_tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, mons_id, plugin_names):
    """
    Load Myth game tags and plugins and output header info for a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if mons_id and mons_id != 'all':
            parse_mons_tag(game_version, tags, data_map, mons_id)
        else:
            print_mons_tags(tags)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def print_mons_tags(tags):
    for mons_id, mons_headers in tags['mons'].items():
        print(mons_id)
        for headers in mons_headers:
            print(f' - {headers[1].name} [{headers[0]}]')

def parse_mons_tag(game_version, tags, data_map, mons_id):
    mons_tag_data = loadtags.get_tag_data(tags, data_map, 'mons', mons_id)

    mons = mons_tag.parse_tag(mons_tag_data)
    
    print_tag(mons, mons_id, tags['mons'][mons_id])

def coll_sequences(tags, data_map, coll_tag):
    collection = myth_headers.decode_string(coll_tag)
    (location, header, data) = loadtags.get_tag_info(tags, data_map, '.256', collection)
    coll_header = myth_collection.parse_collection_header(data, header)
    return (location, f'{header.tag_id} [{header.name}]', myth_collection.parse_sequences(data, coll_header))

def print_tag(mons, mons_id, locations):
    (location, tag_header) = locations[-1]
    print(mons_id, tag_header.name)
    print(location)
    mons_d = mons._asdict()
    for f in mons._fields:
        val = mons_d[f]
        if f == 'attacks':
            for attack_i, attack in enumerate(val):
                if not attack:
                    print(f'{f:<42} [{attack_i}]: None')
                else:
                    attack_d = attack._asdict()
                    for a_f in attack._fields:
                        a_v = attack_d[a_f]
                        if a_f == 'sequences':
                            for seq_i, seq in enumerate(a_v):
                                print(f'{f:<42} [{attack_i}]: {a_f}[{seq_i}]: {seq}')
                        else:
                            print(f'{f:<42} [{attack_i}]: {a_f}: {a_v}')
        else:
            if type(val) is bytes and myth_headers.all_off(val):
                val = f'[00 x {len(val.split(b'\x00'))-1}]'
            elif type(val) is bytes and myth_headers.all_on(val):
                val = f'[FF x {len(val.split(b'\xff'))-1}]'
            print(f'{f:<42} {val}')
            # print(f'[{mons_id}] {f} {val} {locations}')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mons2info.py <game_directory> [<mons_id> [<plugin_names> ...]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    mons_id = None
    plugin_names = []
    if len(sys.argv) > 2:
        mons_id = sys.argv[2]
        if len(sys.argv) > 3:
            plugin_names = sys.argv[3:]

    try:
        main(game_directory, mons_id, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
