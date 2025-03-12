#!/usr/bin/env python3
import sys
import os
import pathlib
import struct

import myth_headers
import mono2tag

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, plugin_names):
    """
    Load Myth game tags and plugins
    """
    try:
        (files, cutscenes) = build_file_list(game_directory, plugin_names)
        (game_version, tags, entrypoint_map, data_map) = build_tag_map(files)

        mono2tag.print_entrypoint_map(entrypoint_map)

        for tag_type, tag_type_tags in tags.items():
            print(f'{tag_type} num={len(tag_type_tags)}')
            for tag_id, tag_headers in tag_type_tags.items():
                latest = tag_headers[-1]
                if tag_type == 'mesh' or len(tag_headers) > 1 or latest[0] in plugin_names:
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

def build_file_list(game_directory, plugin_names=[]):
    files = []
    cutscenes = {}

    for tag_dir in ['tags', 'plugins']:
        tags_dir = pathlib.Path(game_directory, tag_dir)
        if tags_dir.exists():
            files += read_file_headers(tags_dir, plugin_names)

    cutscene_dir = pathlib.Path(game_directory, 'cutscenes')
    if cutscene_dir.exists():
        for cutscene in os.scandir(cutscene_dir):
            if cutscene.is_file() and not cutscene.name.startswith('.'):
                cutscenes[cutscene.name] = cutscene

    return (sorted(set(files)), cutscenes)


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
            header_name = f'\x1b[1m{mono_header.name}\x1b[0m'
            if name != mono_header.name:
                header_name = f'{header_name} [file={name}]'
            plugin_flags = myth_headers.plugin_version_flags(mono_header)
            plugin_dep = myth_headers.plugin_dependency(mono_header)
            pf = f'[{'|'.join([p.name for p in plugin_flags])}] ' if plugin_flags else ''
            dep = f'dep=\x1b[1m{plugin_dep}\x1b[0m ' if plugin_dep else ''
            print(
                f'flags={mono_header.flags} '
                f'v={mono_header.version:<5} '
                f'ck={hex(mono_header.checksum):<10} '
                f'\x1b[1mINCLUDE\x1b[0m[{mono_header.game_version}] '
                f'{mono_header.type.name:<10} '
                f'entry={mono_header.entry_tag_count:<3} '
                f'tags={mono_header.tag_count:<4} '
                f'{header_name} '
                f'{pf}'
                f'{dep}'
            )

        # Take the version from the first tag loaded
        if not game_version:
            game_version = mono_header.game_version

        data = myth_headers.load_file(path)
        data_map[name] = data

        if mono_header.entry_tag_count:
            entrypoints = mono2tag.get_entrypoints(data, mono_header)
            for entry_id, (entry_name, entry_long_name, archive_list) in entrypoints.items():
                current_archive_list = []
                if entry_id in entrypoint_map:
                    current_archive_list = entrypoint_map[entry_id][2]

                entrypoint_map[entry_id] = (entry_name, entry_long_name, current_archive_list + archive_list)

        apppend_tags_from_archive(tags, data, mono_header, name)

    return (game_version, tags, entrypoint_map, data_map)

def apppend_tags_from_archive(tags, data, mono_header, name):
    for (i, tag_header) in mono2tag.get_tags(data, mono_header):
        tag_type_tags = tags.get(tag_header.tag_type, {})

        if tag_header.tag_id in tag_type_tags:
            tag_id_list = tag_type_tags[tag_header.tag_id]
        else:
            tag_id_list = []

        tag_id_list.append((name, tag_header))

        tag_type_tags[tag_header.tag_id] = tag_id_list
        tags[tag_header.tag_type] = tag_type_tags

def read_file_headers(path_dir, plugin_names):
    for dirfile in os.scandir(path_dir):
        dirfile = pathlib.Path(dirfile)
        if (
            dirfile.is_file()
            and not dirfile.name.startswith('.')
            and not dirfile.name == 'scrap.gor'
            and not dirfile.name == 'plugin cache'
        ):
            header_data = myth_headers.load_file(dirfile, myth_headers.SB_MONO_HEADER_SIZE)
            try:
                mono_header = myth_headers.parse_mono_header(dirfile.name, header_data)
                if mono_header.game_version == 1:
                    priority = -1
                else:
                    priority = myth_headers.ArchivePriority[mono_header.type]
                # Only include foundation, patches, addons and named plugins
                if priority < 0 or dirfile.name in plugin_names:
                    plugin_dep = myth_headers.plugin_dependency(mono_header)
                    if plugin_dep:
                        dep_path = (path_dir / plugin_dep)
                        dep_header = myth_headers.load_file(dep_path, myth_headers.SB_MONO_HEADER_SIZE)
                        dep_mono_header = myth_headers.parse_mono_header(dep_path.name, dep_header)
                        dep_priority = myth_headers.ArchivePriority[dep_mono_header.type]
                        yield (
                            dep_priority,
                            dep_mono_header.version,
                            dep_path.name,
                            path_dir,
                            dep_path,
                            dep_mono_header
                        )
                    yield (
                        priority,
                        mono_header.version,
                        dirfile.name,
                        path_dir,
                        dirfile,
                        mono_header
                    )
                else:
                    if DEBUG:
                        header_name = mono_header.name
                        if dirfile.name != mono_header.name:
                            header_name = f'{header_name} [file={dirfile.name}]'

                        plugin_flags = myth_headers.plugin_version_flags(mono_header)
                        plugin_dep = myth_headers.plugin_dependency(mono_header)
                        pf = f'[{'|'.join([p.name for p in plugin_flags])}] ' if plugin_flags else ''
                        dep = f'dep=\x1b[1m{plugin_dep}\x1b[0m ' if plugin_dep else ''
                        print(
                            f'flags={mono_header.flags} '
                            f'v={mono_header.version:<5} '
                            f'ck={hex(mono_header.checksum):<10} '
                            f'EXCLUDE[{mono_header.game_version}] '
                            f'{mono_header.type.name:<10} '
                            f'entry={mono_header.entry_tag_count:<3} '
                            f'tags={mono_header.tag_count:<4} '
                            f'{header_name} '
                            f'{pf}'
                            f'{dep}'
                        )
            except (struct.error, UnicodeDecodeError, ValueError) as e:
                print(f"- [ERROR] \x1b[1m{dirfile.name}\x1b[0m error decoding {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 loadtags.py <game_directory> [<plugin_names...>]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    plugin_names = []
    if len(sys.argv) > 2:
        plugin_names = sys.argv[2:]

    try:
        main(game_directory, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
