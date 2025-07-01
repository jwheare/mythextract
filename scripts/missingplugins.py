#!/usr/bin/env python3
import os
import pathlib
import sys

import reco_tag
import game_headers
import myth_headers
import codec

DEBUG = (os.environ.get('DEBUG') == '1')

def read_binary_headers(root_dir, num_bytes=64):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, 'rb') as f:
                    try:
                        header = myth_headers.parse_header(f.read(num_bytes))
                        if header.tag_type == 'reco':
                            yield file_path
                    except ValueError:
                        pass
            except Exception as e:
                print(f"[!] Failed to read {file_path}: {e}")


def main(input_dir, game_directory):
    """
    Check downloaded films for missing plugins
    """

    input_path = pathlib.Path(input_dir)
    
    # Walk input_path looking for reco_files
    reco_files = []
    for file_match in read_binary_headers(input_path):
        reco_files.append(file_match)

    plugin_values = {}
    for reco_file in reco_files:
        (header, reco_data, reco, game_param, game_data, save_game) = reco_tag.parse_reco_head(
            game_directory, reco_file, head_only=True
        )

        if DEBUG:
            print(reco_file)

        for plugin in game_param.plugin_data:
            if plugin not in plugin_values:
                plugin_values[plugin] = {
                    'installed': is_installed(plugin),
                    'films': []
                }
            plugin_values[plugin]['films'].append(reco_file)

    print('Missing:')
    for plugin_data, meta in plugin_values.items():
        if not meta['installed']:
            print_plugin(plugin_data, meta, fetch_info=True)

    print('Installed:')
    for plugin_data, meta in plugin_values.items():
        if meta['installed']:
            print_plugin(plugin_data, meta, fetch_info=False)

def print_plugin(plugin_data, meta, fetch_info=False):
    game_headers.print_plugins([plugin_data], fetch_info)
    if DEBUG:
        print(f'  - Found in {len(meta['films'])} films:')
        [print(f'    - {p}') for p in meta['films']]

def is_installed(plugin_data):
    plugin_name = codec.decode_string(plugin_data[0])
    plugin_path = pathlib.Path(game_directory) / 'plugins' / plugin_name
    return plugin_path.exists()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <input_dir> <game_directory>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    game_directory = sys.argv[2]
    
    try:
        main(input_dir, game_directory)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
