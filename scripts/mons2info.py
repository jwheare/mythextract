#!/usr/bin/env python3
import sys
import os
import struct

import codec
import myth_collection
import mons_tag
import loadtags
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, mons_id, plugin_names):
    """
    Load Myth game tags and plugins and output header info for a mons
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if mons_id and mons_id != 'all':
            mons = parse_mons_tag(game_version, tags, data_map, mons_id)
            print_tag(mons, mons_id, tags['mons'][mons_id], tags, data_map)
        else:
            # print_mons_debug(game_version, tags, data_map)
            print_mons_tags(tags)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def print_mons_debug(game_version, tags, data_map):
    for mons_id, mons_headers in tags['mons'].items():
        mons = parse_mons_tag(game_version, tags, data_map, mons_id)
        if mons.use_attack_frequency:
            print(mons_id)

def print_mons_tags(tags):
    for mons_id, mons_headers in tags['mons'].items():
        print(mons_id)
        for headers in mons_headers:
            print(f' - {headers[1].name} [{headers[0]}]')

def parse_mons_tag(game_version, tags, data_map, mons_id):
    mons_tag_data = loadtags.get_tag_data(tags, data_map, 'mons', mons_id)
    return mons_tag.parse_tag(mons_tag_data)

def coll_sequences(tags, data_map, coll_tag):
    collection = codec.decode_string(coll_tag)
    (location, header, data) = loadtags.get_tag_info(tags, data_map, '.256', collection)
    coll_header = myth_collection.parse_collection_header(data, header)
    return myth_collection.parse_sequences(data, coll_header)

def print_tag(mons, mons_id, locations, tags, data_map):
    (location, tag_header) = locations[-1]
    print(mons_id, tag_header.name)
    print(location)
    for i, (f, val) in enumerate(mons._asdict().items()):
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
        elif f == 'terrain_costs':
            passability = mons_tag.terrain_passability(mons)
            print(f'{"terrain":<42} | terrain_costs | movement_modifiers | real_passability')
            for terrain_type, terrain_cost in mons.terrain_costs._asdict().items():
                movement_modifier = getattr(mons.movement_modifiers, terrain_type)
                real_passability = passability[terrain_type]
                print(
                    f'{terrain_type:>42} | '
                    f'{terrain_cost:<13} | '
                    f'{movement_modifier:<18} | '
                    f'{real_passability:<16}'
                )
        elif f == 'movement_modifiers':
            pass
        elif f == 'sound_tags':
            for i, sound_tag in enumerate(val):
                sound_type = mons_tag.SoundTypes(mons.sound_types[i])
                print(f'{f:<42} [{i}]: tag={sound_tag} type={sound_type.name}')
        elif f == 'sound_types':
            pass
        elif f == 'sequence_indexes':
            sequences = coll_sequences(tags, data_map, mons.collection_tag)
            for seq, idx in enumerate(val):
                print(f'{f:<42} [{seq:>2}]: {mons_tag.sequence_name(seq):<16} {idx:>3} ', end='')
                sequence = None
                if idx > -1:
                    sequence = sequences[idx]
                    print(f'{sequence['name']}')
                else:
                    print()
        else:
            print(f'{f:<42} {utils.val_repr(val)}')
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
