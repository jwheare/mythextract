#!/usr/bin/env python3
import sys
import os
import pathlib
import struct

import myth_headers
import mono2tag

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, plugin_name):
    """
    Load Myth game tags and plugins
    """
    try:
        (files, cutscenes) = build_file_list(game_directory, plugin_name)
        (game_version, tags, entrypoint_map, data_map) = build_tag_map(files)

        for header_name, entrypoints in entrypoint_map.items():
            mono2tag.print_entrypoints(entrypoints, header_name)

        for tag_type, tag_type_tags in tags.items():
            print(f'{tag_type} num={len(tag_type_tags)}')
            for tag_id, tag_headers in tag_type_tags.items():
                latest = tag_headers[-1]
                if tag_type == 'mesh' or len(tag_headers) > 1 or latest[0] == plugin_name:
                    print(f'{tag_type} {tag_id}')
                    for headers in tag_headers:
                        print(f' - {headers[1].name} [{headers[0]}]')
            print('---')

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def lookup_tag_header(tags, tag_type, tag_id):
    if tag_type in tags and tag_id in tags[tag_type]:
        return tags[tag_type][tag_id][-1]
    return (None, None)

def build_file_list(game_directory, plugin_name=None):
    files = []
    cutscenes = {}

    for tag_dir in ['tags', 'plugins', 'local']:
        tags_dir = pathlib.Path(game_directory, tag_dir)
        if tags_dir.exists():
            files += read_file_headers(tags_dir, plugin_name)

    cutscene_dir = pathlib.Path(game_directory, 'cutscenes')
    if cutscene_dir.exists():
        for cutscene in os.scandir(cutscene_dir):
            if cutscene.is_file() and not cutscene.name.startswith('.'):
                cutscenes[cutscene.name] = cutscene

    return (sorted(files), cutscenes)

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
    game_version = None
    for (pri, ver, name, path_dir, path, mono_header) in files:
        if DEBUG:
            print(
                f'{path_dir.name} - [{mono_header.game_version}] [{mono_header.type}] \x1b[1m{name} - {mono_header.name}\x1b[0m v={mono_header.version} '
                f'entrypoints={mono_header.entry_tag_count} tags={mono_header.tag_count}'
            )

        # Take the version from the first tag loaded
        if not game_version:
            game_version = mono_header.game_version

        data = myth_headers.load_file(path)
        data_map[name] = data

        if mono_header.entry_tag_count:
            entrypoints = mono2tag.get_entrypoints(data, mono_header)
            entrypoint_map[name] = entrypoints

        for (i, tag_header) in mono2tag.get_tags(data, mono_header):
            tag_type_tags = tags.get(tag_header.tag_type, {})

            if tag_header.tag_id in tag_type_tags:
                tag_id_list = tag_type_tags[tag_header.tag_id]
            else:
                tag_id_list = []

            tag_id_list.append((name, tag_header))

            tag_type_tags[tag_header.tag_id] = tag_id_list
            tags[tag_header.tag_type] = tag_type_tags

    return (game_version, tags, entrypoint_map, data_map)


def read_file_headers(path_dir, plugin_name):
    for dirfile in os.scandir(path_dir):
        if dirfile.is_file() and not dirfile.name.startswith('.') and not dirfile.name == 'scrap.gor':
            header_data = myth_headers.load_file(dirfile.path, myth_headers.SB_MONO_HEADER_SIZE)
            try:
                mono_header = myth_headers.parse_mono_header(header_data)
                if mono_header.game_version == 1:
                    priority = -1
                else:
                    priority = myth_headers.ArchivePriority[mono_header.type]
                # Only include foundation, patches, addons and named plugins
                if priority < 0 or dirfile.name == plugin_name:
                    yield (
                        priority,
                        mono_header.version,
                        dirfile.name,
                        path_dir,
                        dirfile.path,
                        mono_header
                    )
                else:
                    if DEBUG:
                        print(
                            f'EXCLUDE {path_dir.name} - [{mono_header.game_version}] [{mono_header.type}] \x1b[1m{dirfile.name} - {mono_header.name}\x1b[0m v={mono_header.version} '
                            f'entrypoints={mono_header.entry_tag_count} tags={mono_header.tag_count}'
                        )
            except ValueError:
                pass
            except (struct.error, UnicodeDecodeError, ValueError) as e:
                print(f"- [ERROR] \x1b[1m{dirfile.name}\x1b[0m error decoding {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 loadtags.py <game_directory> [<plugin_name>]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    plugin_name = None
    if len(sys.argv) > 2:
        plugin_name = sys.argv[2]

    try:
        main(game_directory, plugin_name)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.exit(1)
