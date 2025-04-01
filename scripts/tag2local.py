#!/usr/bin/env python3
import sys
import os
import pathlib
import struct

import myth_headers
import mesh2tags
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, tag_type, tag_id, plugin_names):
    """
    Recursively extracts all referenced tags from a tag into a local tree structure
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        extract_tags(tag_type, tag_id, tags, data_map, plugin_names)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def extract_tags(tag_type, tag_id, tags, data_map, plugin_names):
    all_tag_data = []
    tdg = mesh2tags.TagDataGenerator(tags, data_map, plugin_names)
    for td in tdg.get_tag_data(tag_type, myth_headers.encode_string(tag_id)):
        all_tag_data.append(td)

    output_dir = f'../output/tag2local/{tag_type}/{tag_id}/local'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    if prompt(output_path):
        for (tag_header, tag_data) in all_tag_data:
            file_path = (output_path / f'{myth_headers.local_folder(tag_header)}/{tag_header.name}')
            pathlib.Path(file_path.parent).mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as tag_file:
                tag_file.write(tag_data)

            print(f"Tag extracted. Output saved to {file_path}")

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 tag2local.py <game_directory> <tag_type> <tag_id> [<plugin_names...>]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_names = []
    tag_type = sys.argv[2]
    tag_id = sys.argv[3]
    if len(sys.argv) > 4:
        plugin_names = sys.argv[4:]

    try:
        main(game_directory, tag_type, tag_id, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
