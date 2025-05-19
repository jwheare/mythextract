#!/usr/bin/env python3
import enum
import os
import pathlib
import struct
import sys

import myth_headers
import mono2tag
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
IS_VTFL = (os.environ.get('VTFL') == '1')
FORCE_VTFL = (os.environ.get('FORCE_VTFL') == '1')
UNITY = os.environ.get('UNITY')

UNITY_1_5 = 'Patch 1.5 Unity'
UNITY_1_8_5 = 'Patch 1.8.5 Unity'

LoadReversePlugins = [
    "Magma - The Fallen Levels v2",
    "Magma TFL Multipack",
    "Magma - Shadow III",
    "Magma - Dol Baran v2.1",
]

class PluginFlag(enum.Flag):
    TAGSETS_LAST = enum.auto() # Load in reverse order (mesh plugins then tagsets)
    VTFL = enum.auto() # Compatibility with vTFL
    URL_PLUGIN = enum.auto() # Reliant on plugin named in URL field above
    MESH_LAST = enum.auto() # Force Meshes in this plugin to load last

TagSetRequirements = {
    "TSG Level-Pack v1.4": "TSG Tagset v1.4",
    "JINN Mappack v.1": "JINN Tagset v.1",
    "Blue & Grey Levelpack": "Blue & Grey Tagset",
    "SF_CarnageIslands(v1.0)": "SF_SpecialForces(v1.0)",
    "Green Berets Mappack v1.2": "Green Berets Tagset v1.2",
}

Unity185Plugins = [
    "3DA3 v1.0",
    "A Shattered Visage 1.1",
    "Magma - Ambush II",
    "Magma - Five Legends TFL II",
    "Magma - Flight from Covenant II",
    "Magma - Forest Heart II",
    "Magma - Ghol Rugby M2",
    "Magma - Shadow III",
    "Magma - TFL Multipack v2.6",
    "Magma - The Fallen Levels v2",
    "Magma - The Fallen Lords v1.9",
    "Magma - Valley of Despair",
    "Magma TFL Multipack",
    "Twister v1.3",
]

def unity(plugin):
    if UNITY:
        return UNITY
    elif plugin in Unity185Plugins:
        return UNITY_1_8_5
    else:
        return UNITY_1_5

def main(game_directory, plugin_names):
    """
    Load Myth game tags and plugins
    """
    try:
        (game_version, tags, entrypoint_map, data_map, cutscenes) = load_tags(game_directory, plugin_names)

        mono2tag.print_entrypoint_map(entrypoint_map)

        for tag_type, tag_type_tags in tags.items():
            print(f'{tag_type} num={len(tag_type_tags)}')
            for tag_id, tag_headers in tag_type_tags.items():
                latest = tag_headers[-1]
                if len(tag_headers) > 1 or latest[0] in plugin_names:
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

def load_tags(game_directory, plugin_names=[]):
    (files, cutscenes) = build_file_list(game_directory, plugin_names)
    (game_version, tags, entrypoint_map, data_map) = build_tag_map(files)
    return (game_version, tags, entrypoint_map, data_map, cutscenes)

def build_file_list(game_directory, plugin_names):
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

def locate_tag_data(tags, data_map, tag_type, tag_id, location):
    tag_locations = tags[tag_type].get(tag_id)
    if tag_locations:
        for (tag_location, tag_header) in tag_locations:
            if (tag_location == location):
                tag_start = tag_header.tag_data_offset
                tag_end = tag_start + tag_header.tag_data_size
                tag_header_norm = myth_headers.normalise_tag_header(tag_header)
                return (
                    tag_header_norm,
                    tag_header_norm.value + data_map[location][tag_start:tag_end]
                )
    return (None, None)

def get_tag_data(tags, data_map, tag_type, tag_id):
    (location, tag_header) = lookup_tag_header(tags, tag_type, tag_id)
    if tag_header:
        tag_start = tag_header.tag_data_offset
        tag_end = tag_start + tag_header.tag_data_size
        return myth_headers.encode_header(tag_header) + data_map[location][tag_start:tag_end]

def get_tag_info(tags, data_map, tag_type, tag_id):
    (location, tag_header) = lookup_tag_header(tags, tag_type, tag_id)
    (tag_header, tag_data) = locate_tag_data(tags, data_map, tag_type, tag_id, location)
    return (location, tag_header, tag_data)

def build_tag_map(files):
    tags = {}
    data_map = {}
    entrypoint_map = {}
    game_version = None
    for (order, filename, path_dir, path, mono_header) in files:
        debug_include(mono_header, True, order)

        # Take the version from the first tag loaded
        if not game_version:
            game_version = mono_header.game_version

        data = utils.load_file(path)
        data_map[mono_header.filename] = data

        if mono_header.entry_tag_count:
            entrypoints = mono2tag.get_entrypoints(data, mono_header)
            for entry_id, (entry_name, entry_long_name, archive_list) in entrypoints.items():
                current_archive_list = []
                if entry_id in entrypoint_map:
                    current_archive_list = entrypoint_map[entry_id][2]

                entrypoint_map[entry_id] = (entry_name, entry_long_name, current_archive_list + archive_list)

        append_tags_from_archive(tags, data, mono_header, filename)

    return (game_version, tags, entrypoint_map, data_map)

def append_tags_from_archive(tags, data, mono_header, name):
    for tag_header in myth_headers.get_mono_tags(data, mono_header):
        tag_type_tags = tags.get(tag_header.tag_type, {})

        if tag_header.tag_id in tag_type_tags:
            tag_id_list = tag_type_tags[tag_header.tag_id]
        else:
            tag_id_list = []

        tag_id_list.append((name, tag_header))

        tag_type_tags[tag_header.tag_id] = tag_id_list
        tags[tag_header.tag_type] = tag_type_tags

def debug_include(mono_header, include, order):
    if DEBUG:
        header_name = mono_header.name
        if include:
            header_name = f'\x1b[1m{header_name}\x1b[0m'
        if mono_header.filename != mono_header.name:
            header_name = f'{header_name} [file={mono_header.filename}]'
        plugin_flags = plugin_version_flags(mono_header)
        plugin_dep = plugin_dependency(mono_header)
        pf = f'[{"|".join([p.name for p in plugin_flags])}] ' if plugin_flags else ''
        dep = f'dep=\x1b[1m{plugin_dep}\x1b[0m ' if plugin_dep else ''
        if include:
            included = '\x1b[1mINCLUDE\x1b[0m'
        else:
            included = 'EXCLUDE'
        print(
            f'flags={mono_header.flags} '
            f'v={mono_header.version:<5} '
            f'order={"|".join(str(o) for o in order):<6} '
            f'ck=0x{mono_header.checksum.hex():<10} '
            f'{included}[{mono_header.game_version}] '
            f'{mono_header.type.name:<10} '
            f'entry={mono_header.entry_tag_count:<3} '
            f'tags={mono_header.tag_count:<4} '
            f'{header_name} '
            f'{pf}'
            f'{dep}'
        )

def archive_priority(mono_header):
    return myth_headers.ArchivePriority[mono_header.type]

def plugin_dependency(mono_header):
    if mono_header.type != myth_headers.ArchiveType.PLUGIN:
        return
    hard_coded = TagSetRequirements.get(mono_header.filename)
    flag = plugin_version_flags(mono_header)
    if hard_coded:
        return hard_coded
    elif flag and PluginFlag.URL_PLUGIN in flag and mono_header.description:
        return mono_header.description

def plugin_version_flags(mono_header):
    if mono_header.type == myth_headers.ArchiveType.PLUGIN:
        try:
            return PluginFlag(mono_header.version)
        except ValueError:
            return None

def dep_plugin(path_dir, plugin_dep, sub_order):
    dep_path = (path_dir / plugin_dep)
    dep_header = utils.load_file(dep_path, myth_headers.SB_MONO_HEADER_SIZE)
    dep_mono_header = myth_headers.parse_mono_header(dep_path.name, dep_header)
    return (0, sub_order, dep_path, dep_mono_header)

def append_dep_plugin(plugins, path_dir, plugin_dep, sub_order):
    plugins.append(dep_plugin(path_dir, plugin_dep, sub_order))
    sub_order += 1
    return sub_order

def read_file_headers(path_dir, plugin_names):
    # Build an initial plugin list
    plugins = []
    for dirfile in os.scandir(path_dir):
        dirfile = pathlib.Path(dirfile)
        if (
            dirfile.is_file()
            and not dirfile.name.startswith('.')
            and not dirfile.name == 'scrap.gor'
            and not dirfile.name == 'plugin cache'
        ):
            header_data = utils.load_file(dirfile, myth_headers.SB_MONO_HEADER_SIZE)
            try:
                mono_header = myth_headers.parse_mono_header(dirfile.name, header_data)
                if mono_header.game_version == 1:
                    priority = -1
                else:
                    priority = archive_priority(mono_header)
                if (
                    # Include foundation, patches
                    priority < -1 or
                    # Include patch template addons, not sure if this will always hold true
                    # but we want to exclude large detail addons by default which all seem to
                    # have version=101
                    (priority == -1 and mono_header.version < 100)
                ):
                    plugins.append((priority, mono_header.version, dirfile, mono_header))
                elif len(plugin_names) and dirfile.name == plugin_names[-1]:
                    # Hack for now, treat last plugin passed in as the mesh/entrypoint plugin
                    plugins.append((priority, 0, dirfile, mono_header))

                    # Deal with other named plugins and dependencies, maintaining this sub order
                    sub_order = 0
                    plugin_dep = plugin_dependency(mono_header)
                    plugin_flag = plugin_version_flags(mono_header)

                    # 1. Mesh defined dependencies
                    # TODO handle mesh tag defined dependencies (not widely used)

                    # 2. Plugin defined dependencies
                    if plugin_dep:
                        sub_order = append_dep_plugin(plugins, path_dir, plugin_dep, sub_order)

                    # 3. vTFL Unity
                    # TODO handle mesh tag enforced vtfl
                    if FORCE_VTFL or (IS_VTFL and plugin_flag and PluginFlag.VTFL in plugin_flag):
                        sub_order = append_dep_plugin(plugins, path_dir, unity(dirfile.name), sub_order)

                    # 4. Manual tagsets (other named plugins in order)
                    if len(plugin_names) > 1:
                        for plugin_name in plugin_names[:-1]:
                            if not mono_header.entry_tag_count:
                                sub_order = append_dep_plugin(plugins, path_dir, plugin_name, sub_order)
                else:
                    debug_include(mono_header, False, (archive_priority(mono_header),0))
            except (struct.error, UnicodeDecodeError, ValueError) as e:
                print(f"- [ERROR] \x1b[1m{dirfile.name}\x1b[0m error decoding {e}")
    
    # BROKEN logic for COMPATIBILITY
    load_order_enforced = False
    all_tagsets_last = False
    for (plugin_priority, sub_order, plugin_path, plugin_header) in plugins:
        plugin_flag = plugin_version_flags(plugin_header)
        # Conditions that make all non-mesh plugins load after the mesh plugin

        # 1. harcoded non-mesh plugin
        if not plugin_header.entry_tag_count:
            if not load_order_enforced and plugin_header.filename in [
                "Blue & Grey Tagset",
            ]:
                all_tagsets_last = True
                break
        # 2. any mesh plugin with the TAGSETS_LAST version flag
        elif not load_order_enforced and plugin_flag and PluginFlag.TAGSETS_LAST in plugin_flag:
            all_tagsets_last = True
            break
        # 3. hardcoded list of mesh plugins
        elif plugin_header.filename in LoadReversePlugins:
            all_tagsets_last = True
            break

        # Condition that prevents conditions 1 and 2 above and reverses the effect of any of the 3 conditions above
        # 0. Any plugin with the MESH_LAST version flag that doesn't match any of the 3 conditions above
        if plugin_flag and PluginFlag.MESH_LAST in plugin_flag:
            load_order_enforced = True
            all_tagsets_last = False

    # Setup plugin priority order
    # determine the order index of each plugin:
    # ??? NOTE: 0 is possibly bugged, these will actually be treated as tagsets (2 or 4)
    # ??? 0. all map plugins besides our entrypoint plugin
    # ??? (we aren't loading a mesh from them, so everything should override them)
    # 1. entrypoint that must load first
    # 2. normal tagsets (no such thing as tagsets that must load first)
    # 3. normal entrypoint
    # 4. tagsets that must load last
    # 5. entrypoint that must load last
    for (plugin_priority, sub_order, plugin_path, plugin_header) in plugins:
        # Hack for now, treat last plugin passed in as the mesh/entrypoint plugin
        is_entry_plugin = bool(len(plugin_names)) and plugin_header.filename == plugin_names[-1]
        is_core_plugin = plugin_priority < 0
        plugin_flag = plugin_version_flags(plugin_header)

        if is_core_plugin:
            # Just use the standard subzero priority for core plugins
            order_index = plugin_priority
        elif is_entry_plugin:
            # Mesh entrypoint plugin
            if not all_tagsets_last and not load_order_enforced and mesh_plugin_must_load_first(plugin_flag):
                order_index = 1
            elif all_tagsets_last or load_order_enforced or not mesh_plugin_must_load_last(plugin_flag):
                order_index = 3
            else:
                order_index = 5
        else:
            # All other tagsets
            if not all_tagsets_last and (load_order_enforced or not tagset_plugin_must_load_last(plugin_flag)):
                order_index = 2
            else:
                order_index = 4

        yield (
            (order_index, sub_order),
            plugin_header.filename,
            path_dir,
            plugin_path,
            plugin_header
        )

def mesh_plugin_must_load_first(plugin_flag):
    if plugin_flag and PluginFlag.TAGSETS_LAST in plugin_flag:
        return True
    else:
        return False

def mesh_plugin_must_load_last(plugin_flag):
    if plugin_flag and PluginFlag.MESH_LAST not in plugin_flag:
        return True
    else:
        return False

def tagset_plugin_must_load_last(plugin_flag):
    if plugin_flag and PluginFlag.TAGSETS_LAST in plugin_flag:
        return True
    else:
        return False

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
