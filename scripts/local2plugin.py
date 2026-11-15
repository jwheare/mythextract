#!/usr/bin/env python3
import sys
import os
import pathlib

import myth_headers

DEBUG = (os.environ.get('DEBUG') == '1')

def main(local_folder, plugin_name, plugin_desc):
    """
    Build a local folder of tags into a plugin
    """

    if not plugin_name:
        plugin_name = input(f"Choose a plugin name: ").strip().lower()

    if not plugin_desc:
        plugin_desc = input(f"Choose a plugin description (optional): ").strip().lower()

    tag_list = list(read_tags(local_folder))
    plugin_data = myth_headers.make_plugin(tag_list, plugin_name, plugin_desc)
    output_dir = '../output/local2plugin'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    plugin_path = output_path / plugin_name
    if prompt(plugin_path):
        output_path.mkdir(parents=True, exist_ok=True)
        with open(plugin_path, 'wb') as plugin_file:
            plugin_file.write(plugin_data)

def prompt(plugin_path):
    exists = "[Exists] " if plugin_path.exists() else ""
    response = input(f"{exists}Save plugin to: {plugin_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def read_tags(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if DEBUG:
                print(file_path, end='')
            try:
                with open(file_path, 'rb') as f:
                    try:
                        header_data = f.read(myth_headers.TAG_HEADER_SIZE)
                        header = myth_headers.parse_header(header_data)
                        tag_data = header_data + f.read()
                        if DEBUG:
                            print(f" √")
                        yield (header, tag_data)
                    except ValueError:
                        if DEBUG:
                            print(f" .")
                        pass
            except Exception as e:
                if DEBUG:
                    print(f" ! failed: {e}")
                else:
                    print(f"! failed: {file_path} {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <local_folder> [<plugin_name> [<plugin_desc]]")
        sys.exit(1)
    
    local_folder = sys.argv[1]

    plugin_name = None
    if len(sys.argv) > 2:
        plugin_name = sys.argv[2]

    plugin_desc = None
    if len(sys.argv) > 3:
        plugin_desc = sys.argv[3]

    try:
        main(local_folder, plugin_name, plugin_desc)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
