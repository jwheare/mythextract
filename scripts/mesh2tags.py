#!/usr/bin/env python3
import sys
import os
import pathlib
import struct

import codec
import tag2local
import mesh2info
import mono2tag
import loadtags
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
IS_VTFL = (os.environ.get('VTFL') == '1')

def main(game_directory, level, plugin_names):
    """
    Recursively extracts all referenced tags from a mesh into a local tree structure
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if level:
            (mesh_id, header_name, entry_name) = mesh2info.parse_level(level, tags)
            vtfl = ' [vtfl]' if IS_VTFL else ''
            print(f'mesh={mesh_id} file=[{header_name}] [{entry_name}]{vtfl}')
            extract_mesh_tags(mesh_id, tags, data_map, plugin_names)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def extract_mesh_tags(mesh_id, tags, data_map, plugin_names):
    (mesh_location, mesh_tag_header) = loadtags.lookup_tag_header(
        tags, 'mesh', mesh_id
    )
    tdg = tag2local.TagDataGenerator(tags, data_map, plugin_names)
    all_tag_data = []
    for td in tdg.get_tag_data('mesh', codec.encode_string(mesh_id)):
        all_tag_data.append(td)

    output_dir = f'../output/mesh2tags/{mesh_tag_header.name}/local'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    if prompt(output_path):
        for (tag_header, tag_data) in all_tag_data:
            file_path = (output_path / f'{utils.local_folder(tag_header)}/{tag_header.name}')
            pathlib.Path(file_path.parent).mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as tag_file:
                tag_file.write(tag_data)

            print(f"Tag extracted. Output saved to {file_path}")

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
