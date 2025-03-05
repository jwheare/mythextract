#!/usr/bin/env python3
import sys
import os
import struct

import mesh_tag
import mesh2info
import mono2tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, level, plugin_name):
    """
    Load Myth game tags and plugins and output scripting actions for a mesh
    """
    (files, cutscenes) = loadtags.build_file_list(game_directory, plugin_name)
    (game_version, tags, entrypoint_map, data_map) = loadtags.build_tag_map(files)

    try:
        if level:
            for mesh_id in mesh2info.mesh_entries(level, entrypoint_map, tags):
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

        action_vars = []
        if len(act['parameters']):
            if act['flags']:
                action_vars.append(','.join([f.name.lower() for f in act['flags']]))
            if act['expiration_mode'] != mesh_tag.ActionExpiration.TRIGGER:
                action_vars.append(f'expiry={act['expiration_mode'].name.lower()}')
            if act['trigger_time_start']:
                action_vars.append(f'delay={round(act['trigger_time_start'], 3)}s')
            if act['trigger_time_duration']:
                action_vars.append(f'dur={round(act['trigger_time_duration'], 3)}s')

        if len(act['parameters']):
            id_prefix = f'[{action_id}] '
        else:
            id_prefix = '        '
        line = f'{id_prefix}{indent_space}{prefix}{act['name']}'
        if mesh_tag.ActionFlag.INITIALLY_ACTIVE in act['flags']:
            print(f'\x1b[1m{line}\x1b[0m')
        else:
            print(line)
        for p in act['parameters']:
            print(f'        {indent_space}- {p['name']} {p['type'].name}={p['values']}')

        if len(action_vars):
            print(f'\x1b[3m[{' '.join(action_vars)}]\x1b[0m')

        print()

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
    except BrokenPipeError:
        sys.exit(1)
