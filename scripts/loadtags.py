#!/usr/bin/env python3
import sys
import os
import pathlib
import struct
import signal

import myth_headers
import mono2tag

DEBUG = (os.environ.get('DEBUG') == '1')
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def main(game_directory, plugin_name):
    """
    Load Myth II game tags and plugins
    """
    try:
        files = build_file_list(game_directory, plugin_name)
        (tags, entrypoint_map, data_map) = build_tag_map(files)

        for header_name, entrypoints in entrypoint_map.items():
            mono2tag.print_entrypoints(entrypoints, header_name)

        for tag_type, tag_type_tags in tags.items():
            print(tag_type, len(tag_type_tags))
            for tag_id, tag_headers in tag_type_tags.items():
                latest = tag_headers[-1]
                if len(tag_headers) > 1 or latest[0] == plugin_name:
                    print(f'{tag_type} {tag_id} [{latest[0]}] {latest[1].name}')
            print('---')

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def lookup_tag_header(tags, tag_type, tag_id):
    if tag_type in tags and tag_id in tags[tag_type]:
        return tags[tag_type][tag_id][-1]
    return (None, None)

def build_file_list(game_directory, plugin_name):
    files = []

    for tag_dir in ['tags', 'plugins', 'local']:
        tags_dir = pathlib.Path(game_directory, tag_dir)
        files += read_file_headers(tags_dir, plugin_name)

    return sorted(files)

def get_tag_data(tags, data_map, tag_type, tag_id):
    (location, tag_header) = lookup_tag_header(tags, tag_type, tag_id)
    if tag_header:
        tag_start = tag_header.tag_data_offset
        tag_end = tag_start + tag_header.tag_data_size
        return myth_headers.encode_header(tag_header) + data_map[location][tag_start:tag_end]

def build_tag_map(files):
    tags = {}
    data_map = {}
    entrypoint_map = {}
    for (pri, ver, name, path_dir, path, header) in files:
        if DEBUG:
            print(
                f'{path_dir.name} - [{header.type}] \x1b[1m{header.name}\x1b[0m v={header.version} '
                f'entrypoints={header.entry_tag_count} tags={header.tag_list_count}'
            )

        data = myth_headers.load_file(path)
        data_map[header.name] = data

        if header.entry_tag_count:
            entrypoints = mono2tag.get_entrypoints(data, header)
            entrypoint_map[header.name] = entrypoints

        for (i, tag_header) in mono2tag.get_tags(data, header):
            tag_type_tags = tags.get(tag_header.tag_type, {})

            if tag_header.tag_id in tag_type_tags:
                tag_id_list = tag_type_tags[tag_header.tag_id]
            else:
                tag_id_list = []

            tag_id_list.append((header.name, tag_header))

            tag_type_tags[tag_header.tag_id] = tag_id_list
            tags[tag_header.tag_type] = tag_type_tags

    return (tags, entrypoint_map, data_map)


def read_file_headers(path_dir, plugin_name):
    for dirfile in os.scandir(path_dir):
        if dirfile.is_file() and not dirfile.name.startswith('.'):
            header_data = myth_headers.load_file(dirfile.path, myth_headers.SB_MONO_HEADER_SIZE)
            try:
                header = myth_headers.parse_sb_mono_header(header_data)
                priority = myth_headers.ArchivePriority[header.type]
                # Only include foundation, patches, addons and named plugins
                if priority < 0 or header.name == plugin_name:
                    yield (
                        priority,
                        header.version,
                        dirfile.name,
                        path_dir,
                        dirfile.path,
                        header
                    )
                else:
                    if DEBUG:
                        print(
                            f'EXCLUDE {path_dir.name} - [{header.type}] \x1b[1m{header.name}\x1b[0m v={header.version} '
                            f'entrypoints={header.entry_tag_count} tags={header.tag_list_count}'
                        )
            except ValueError:
                pass
            except (struct.error, UnicodeDecodeError, ValueError) as e:
                print(f"- [ERROR] \x1b[1m{dirfile.name}\x1b[0m error decoding {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 loadtags.py <game_directory> [<plugin>]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    plugin_name = None
    if len(sys.argv) > 2:
        plugin_name = sys.argv[2]

    try:
        main(game_directory, plugin_name)
    except KeyboardInterrupt:
        sys.exit(130)
