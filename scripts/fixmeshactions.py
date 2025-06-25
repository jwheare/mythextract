#!/usr/bin/env python3
import sys
import os
import pathlib
import struct

import myth_headers
import mesh_tag
import mesh2info
import mono2tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')
FORCE = (os.environ.get('FORCE') == '1')

def main(game_directory, level, plugin_names):
    """
    Parse a Myth II mesh tag file removes extra data from actions buffer
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if level:
            (mesh_id, header_name, entry_name) = mesh2info.parse_level(level, tags)
            print(f'mesh={mesh_id} file=[{header_name}] [{entry_name}]')
            mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
            fix_mesh_actions(mesh_tag_data)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def fix_mesh_actions(mesh_tag_data):
    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    tag_header = myth_headers.parse_header(mesh_tag_data)

    (actions, action_remainder) = mesh_tag.parse_map_actions(mesh_header, mesh_tag_data)
    remainder_size = len(action_remainder)
    map_action_count = len(actions)
    print('actions', map_action_count)
    print('remaining action data', remainder_size)

    action_size_diff = mesh_header.map_action_buffer_size - remainder_size
    map_action_start = mesh_tag.get_offset(mesh_header.map_actions_offset)
    map_action_end = map_action_start + action_size_diff
    map_action_data = mesh_tag_data[map_action_start:map_action_end]

    if FORCE or remainder_size:
        fixed_tag_data = mesh_tag.rewrite_action_data(map_action_count, map_action_data, mesh_tag_data)
        
        fixed_path = pathlib.Path(sys.path[0], f'../output/fixed_mesh_actions/meshes/{tag_header.name}').resolve()
        if prompt(fixed_path):
            pathlib.Path(fixed_path.parent).mkdir(parents=True, exist_ok=True)
            with open(fixed_path, 'wb') as fixed_tag_file:
                fixed_tag_file.write(fixed_tag_data)

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> [<level> [<plugin_names...>]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_names = []
    if len(sys.argv) > 2:
        level = sys.argv[2]
        if len(sys.argv) > 3:
            plugin_names = sys.argv[3:]

    try:
        main(game_directory, level, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
