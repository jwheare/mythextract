#!/usr/bin/env python3
import sys
import os
import struct

import myth_headers
import mesh_tag
import mesh2info
import mono2tag
import loadtags


DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, level, plugin_name):
    """
    Load Myth game tags and plugins and output scripting actions for a mesh
    """
    try:
        (files, cutscenes) = loadtags.build_file_list(game_directory, plugin_name)
        (game_version, tags, entrypoint_map, data_map) = loadtags.build_tag_map(files)

        if level:
            if level.startswith('file='):
                file = level[5:]
                mesh_tag_data = myth_headers.load_file(file)
                parse_mesh_actions(mesh_tag_data)
            else:
                for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags):
                    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
                    parse_mesh_actions(mesh_tag_data)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_mesh_actions(mesh_tag_data):
    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    tag_header = myth_headers.parse_header(mesh_tag_data)

    (actions, action_remainder) = mesh_tag.parse_map_actions(mesh_header, mesh_tag_data)
    print_actions(actions, tag_header)

    if action_remainder:
        print(f'ACTION REMAINDER {len(action_remainder)}')
        print(action_remainder.hex())

def print_actions(actions, tag_header):
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
            if act['trigger_time_lower_bound']:
                action_vars.append(f'delay={round(act['trigger_time_lower_bound'], 3)}s')
            if act['trigger_time_delta']:
                action_vars.append(f'dur={round(act['trigger_time_delta'], 3)}s')

        if len(act['parameters']):
            id_prefix = f'[{action_id}] '
        else:
            id_prefix = '        '
        # tag_prefix = f'{tag_header.tag_type}={tag_header.tag_id} {tag_header.name} '
        tag_prefix = ''
        line = f'{id_prefix}{indent_space}{prefix}{act['name']}'
        if mesh_tag.ActionFlag.INITIALLY_ACTIVE in act['flags']:
            print(f'{tag_prefix}\x1b[1m{line}\x1b[0m')
        else:
            print(f'{tag_prefix}{line}')
        for p in act['parameters']:
            print(f'{tag_prefix}        {indent_space}- {p['name']} {p['type'].name}={p['elements']}')

        if len(action_vars):
            print(f'{tag_prefix}\x1b[3m[{' '.join(action_vars)}]\x1b[0m')

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
        sys.stdout = None
        sys.exit(1)
