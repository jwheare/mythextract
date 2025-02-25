#!/usr/bin/env python3
import sys
import os
import struct
import signal

import myth_headers
import mesh_tag
import mono2tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def main(game_directory, level, plugin_name):
    """
    Load Myth II game tags and plugins and output header, markers and scripting info for a mesh
    """
    files = loadtags.build_file_list(game_directory, plugin_name)
    (tags, entrypoint_map, data_map) = loadtags.build_tag_map(files)

    try:
        if level:
            if level == 'all':
                for header_name, entrypoints in entrypoint_map.items():
                    for mesh_id, (entry_name, entry_long_name) in entrypoints.items():
                        print(f'mesh={mesh_id} file=[{header_name}] [{entry_name}] [{entry_long_name}]')
                        parse_mesh_tag(tags, data_map, mesh_id)
            else:
                (mesh_id, header_name, entry_name, entry_long_name) = parse_level(level, entrypoint_map)
                print(f'mesh={mesh_id} file=[{header_name}] [{entry_name}] [{entry_long_name}]')
                parse_mesh_tag(tags, data_map, mesh_id)
        else:
            for header_name, entrypoints in entrypoint_map.items():
                mono2tag.print_entrypoints(entrypoints, header_name)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_level(level, entrypoint_map):
    ret = None
    level_mesh = level[5:] if level.startswith('mesh=') else None
    for header_name, entrypoints in entrypoint_map.items():
        for mesh_id, (entry_name, entry_long_name) in entrypoints.items():
            if level_mesh:
                if level_mesh == mesh_id:
                    ret = (mesh_id, header_name, entry_name, entry_long_name)
            elif entry_name.startswith(f'{level} '):
                ret = (mesh_id, header_name, entry_name, entry_long_name)
    if ret:
        return ret
    else:
        print("Invalid level")
        sys.exit(1)

def parse_mesh_tag(tags, data_map, mesh_id):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)

    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    print_header(mesh_header)

    (palette, orphans) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)
    print_markers(tags, palette, orphans)

    (actions, action_remainder) = mesh_tag.parse_map_actions(mesh_header, mesh_tag_data)
    print_actions(actions)

    if action_remainder:
        print(f'ACTION REMAINDER {len(action_remainder)}')
        print(action_remainder.hex())

def print_header(mesh_header):
    mhd = mesh_header._asdict()
    for f in mesh_header._fields:
        val = mhd[f]
        if type(val) is bytes and myth_headers.all_off(val):
            val = f'[00 x {len(val.split(b'\x00'))-1}]'
        elif type(val) is bytes and myth_headers.all_on(val):
            val = f'[FF x {len(val.split(b'\xff'))-1}]'
        print(f'{f:<42} {val}')

def print_markers(tags, palette, orphans):
    for palette_type, p_list in palette.items():
        for palette_index, p_val in enumerate(p_list):
            tag_id = p_val['tag']
            (location, tag_header) = loadtags.lookup_tag_header(tags, mesh_tag.Marker2Tag.get(palette_type), tag_id)
            tag_header_print = f'[{tag_header.name}] ' if tag_header else ''
            flag_info = mesh_tag.palette_flag_info(p_val['flags'])
            flags = f'(flags={'/'.join(flag_info)}) ' if len(flag_info) else ''
            netgame_info = mesh_tag.netgame_flag_info(p_val['netgame_flags'])
            netgame = f'(netgame={'/'.join(netgame_info)}) ' if len(netgame_info) else ''
            print(
                f'{palette_type} {palette_index:<2} '
                f'[{tag_id}] {tag_header_print}'
                f'team={p_val['team_index']} '
                f'{flags}'
                f'{netgame}'
                f'count={p_val['_unreliable_count']}? '
            )

            for marker_id, marker in p_val['markers'].items():

                flag_info = mesh_tag.marker_flag_info(marker['flags'])
                flags = f'(flags={'/'.join(flag_info)}) ' if len(flag_info) else ''

                difficulty = f'(diff={mesh_tag.difficulty(marker['min_difficulty']).lower()}) ' if marker['min_difficulty'] else ''
                print(
                    f'{palette_type} {palette_index:<2} '
                    f'[{tag_id}] {tag_header_print}'
                    f'- {marker_id:<5} '
                    f'{flags}'
                    f'{difficulty}'
                    f'facing={marker['facing']:06.2f} '
                    f'pos={[round(po, 2) for po in marker['pos']]} '
                )
            print('-')

    if orphans['count']:
        print('---')
        print('ORPHANS')
        for marker_type, type_orphans in orphans['markers'].items():
            if len(type_orphans):
                for marker_id, orphan_info in type_orphans.items():
                    print(
                        f'O.{marker_type} {orphan_info['palette_index']:<2} - '
                        f'- {marker_id:<5} '
                        # f'flags={orphan_info['flags']} '
                        f'min_diff={orphan_info['min_difficulty']} '
                        # f'facing={orphan_info['facing']:06.2f} '
                        # f'pos={[round(po, 2) for po in orphan_info['pos']]} '
                    )

def print_actions(actions):
    for i, (action_id, act) in enumerate(actions.items(), 1):
        indent_space = act['indent'] * '  '
        prefix = ''
        if act['type']:
            prefix = f'{act['type'].upper()}.'
        line = f'{i:03} [{action_id}] {indent_space}{prefix}{act['name']}'
        if mesh_tag.ActionFlag.INITIALLY_ACTIVE in act['flags']:
            print(f'\x1b[1m{line}\x1b[0m')
        else:
            print(line)
        for p in act['parameters']:
            if p['name'] != 'name':
                print(' -', p['name'], p['type']._name_, p['values'])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mesh2info.py <game_directory> [<level> [plugin_name]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_name = None
    if len(sys.argv) > 2:
        level = sys.argv[2]
        if len(sys.argv) == 4:
            plugin_name = sys.argv[3]

    try:
        main(game_directory, level, plugin_name)
    except KeyboardInterrupt:
        sys.exit(130)
