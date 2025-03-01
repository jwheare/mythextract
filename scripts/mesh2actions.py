#!/usr/bin/env python3
import sys
import os
import struct
import signal

import mesh_tag
import mesh2info
import mono2tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def main(game_directory, level, plugin_name):
    """
    Load Myth game tags and plugins and output scripting actions for a mesh
    """
    (files, cutscenes) = loadtags.build_file_list(game_directory, plugin_name)
    (game_version, tags, entrypoint_map, data_map) = loadtags.build_tag_map(files)

    try:
        if level:
            for mesh_id in mesh2info.mesh_entries(level, entrypoint_map):
                parse_mesh_actions(game_version, tags, data_map, mesh_id)
        else:
            for header_name, entrypoints in entrypoint_map.items():
                mono2tag.print_entrypoints(entrypoints, header_name)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_mesh_actions(game_version, tags, data_map, mesh_id):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
    mesh_header = mesh_tag.parse_header(mesh_tag_data)

    (actions, action_remainder) = mesh_tag.parse_map_actions(game_version, mesh_header, mesh_tag_data)
    print_actions(actions)

    if action_remainder:
        print(f'ACTION REMAINDER {len(action_remainder)}')
        print(action_remainder.hex())

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
        print("Usage: python3 mesh2actions.py <game_directory> [<level> [plugin_name]]")
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
