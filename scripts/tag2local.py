#!/usr/bin/env python3
import sys
import os
import pathlib
import struct

import myth_headers
import myth_tags
import mesh_tag
import myth_collection
import myth_sound
import myth_projectile
import mons_tag
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
    (location, header) = loadtags.lookup_tag_header(
        tags, tag_type, tag_id
    )
    if not header:
        print(f'Tag not found: {tag_type.upper()}.{tag_id}')
        sys.exit(1)
    all_tag_data = []
    tdg = TagDataGenerator(tags, data_map, plugin_names)
    for td in tdg.get_tag_data(tag_type, myth_headers.encode_string(tag_id)):
        all_tag_data.append(td)

    output_dir = f'../output/tag2local/{tag_type}.{header.name}/local'
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

class TagDataGenerator:
    FETCHED = {}

    def __init__(self, tags, data_map, plugin_names):
        self.tags = tags
        self.data_map = data_map
        self.plugin_names = plugin_names

    def fetched_check(self, tag_type, tag_id):
        if tag_type not in self.FETCHED:
            self.FETCHED[tag_type] = {}
        if tag_id in self.FETCHED[tag_type]:
            return True
        else:
            self.FETCHED[tag_type][tag_id] = True
            return False

    def get_tag_data(self, tag_type, tag_id, tree=[]):
        if self.fetched_check(tag_type, tag_id):
            return

        if myth_headers.all_on(tag_id) or myth_headers.all_off(tag_id):
            return
        (location, tag_header, tag_data) = loadtags.get_tag_info(
            self.tags, self.data_map, tag_type, myth_headers.decode_string(tag_id)
        )
        if tag_data:
            # Copy otherwise this list is just a reference to the original list from
            # when the function was defined and will keep growing
            tree = tree.copy()
            tree.append((location, tag_header))
            if tag_header.tag_type == 'mesh':
                mesh_header = mesh_tag.parse_header(tag_data)
                yield from self.get_tag_data('stli', mesh_header.difficulty_level_override_string_list_tag)
                yield from self.get_tag_data('stli', mesh_header.hints_string_list_tag)
                yield from self.get_tag_data('stli', mesh_header.map_description_string_list_tag)
                yield from self.get_tag_data('stli', mesh_header.picture_caption_string_list_tag)
                yield from self.get_tag_data('stli', mesh_header.team_names_override_string_list_tag)
                yield from self.get_tag_data('text', mesh_header.pregame_storyline_tag)
                yield from self.get_tag_data('.256', mesh_header.landscape_collection_tag)
                yield from self.get_tag_data('.256', mesh_header.overhead_map_collection_tag)
                yield from self.get_tag_data('.256', mesh_header.postgame_collection_tag)
                yield from self.get_tag_data('.256', mesh_header.pregame_collection_tag)
                yield from self.get_tag_data('wind', mesh_header.wind_tag)
                yield from self.get_tag_data('meli', mesh_header.mesh_lighting_tag)
                yield from self.get_tag_data('soun', mesh_header.narration_sound_tag)
                yield from self.get_tag_data('amso', mesh_header.global_ambient_sound_tag)
                yield from self.get_tag_data('part', mesh_header.particle_system_tag)
                yield from self.get_tag_data('conn', mesh_header.connector_tag)
                yield from self.get_tag_data('medi', mesh_header.media_tag)

                # marker tags
                (palette, _) = mesh_tag.parse_markers(mesh_header, tag_data)
                for palette_type, p_list in palette.items():
                    for p_val in p_list:
                        tag_type = mesh_tag.Marker2Tag.get(palette_type)
                        yield from self.get_tag_data(mesh_tag.Marker2Tag.get(palette_type), myth_headers.encode_string(p_val['tag']), tree)

                # action tags
                (actions, _) = mesh_tag.parse_map_actions(mesh_header, tag_data)
                for (action_id, act) in actions.items():
                    if act['type'] == 'soun':
                        for p in act['parameters']:
                            if p['type'] == mesh_tag.ParamType.SOUND:
                                for el in p['elements']:
                                    yield from self.get_tag_data('soun', myth_headers.encode_string(el), tree)
                    elif act['type'] == 'ligh':
                        for p in act['parameters']:
                            if p['type'] == mesh_tag.ParamType.PROJECTILE:
                                for el in p['elements']:
                                    yield from self.get_tag_data('proj', myth_headers.encode_string(el), tree)

            elif tag_header.tag_type == 'soun':
                soun = myth_sound.parse_soun_header(tag_data)
                yield from self.get_tag_data('stli', soun.subtitle_string_list_tag, tree)

            elif tag_header.tag_type == 'amso':
                amso = myth_sound.parse_amso(tag_data)
                for s in amso.sound_tags:
                    yield from self.get_tag_data('soun', s, tree)

            elif tag_header.tag_type == 'lpgr':
                lpgr = myth_projectile.parse_lpgr(tag_data)
                yield from self.get_tag_data('core', lpgr.collection_reference_tag, tree)
                yield from self.get_tag_data('phys', lpgr.physics_tag, tree)
                yield from self.get_tag_data('lpgr', lpgr.chain_to_lpgr_tag, tree)
                yield from self.get_tag_data('meli', lpgr.local_light_tag, tree)

            elif tag_header.tag_type == 'core':
                core = myth_collection.parse_collection_ref(tag_data)
                yield from self.get_tag_data('.256', myth_headers.encode_string(core.collection_tag), tree)

            elif tag_header.tag_type == 'unit':
                (mons, core) = mons_tag.parse_unit(tag_data)
                yield from self.get_tag_data('mons', mons, tree)
                yield from self.get_tag_data('core', core, tree)

            elif tag_header.tag_type == 'conn':
                conn = myth_tags.parse_connector(tag_data)
                yield from self.get_tag_data('core', conn.collection_reference_tag, tree)

            elif tag_header.tag_type == 'part':
                part = myth_tags.parse_particle_sys(tag_data)
                yield from self.get_tag_data('core', part.collection_reference_tag, tree)
                yield from self.get_tag_data('amso', part.ambient_sound_tag, tree)
                yield from self.get_tag_data('lpgr', part.splash_local_projectile_group_tag, tree)

            elif tag_header.tag_type == 'medi':
                media = myth_tags.parse_media(tag_data)
                yield from self.get_tag_data('core', media.collection_reference_tag, tree)
                yield from self.get_tag_data('lpgr', media.surface_effect_local_projectile_group_tag, tree)
                for prgr in media.projectile_group_tags:
                    yield from self.get_tag_data('prgr', prgr, tree)

            elif tag_header.tag_type == 'prgr':
                (prgr_head, proj_list) = myth_projectile.parse_prgr(tag_data)
                yield from self.get_tag_data('meef', prgr_head.mesh_effect, tree)
                yield from self.get_tag_data('soun', prgr_head.sound, tree)
                yield from self.get_tag_data('lpgr', prgr_head.local_projectile_group, tree)
                for proj in proj_list:
                    yield from self.get_tag_data('proj', proj.projectile_tag, tree)
                    yield from self.get_tag_data('proj', proj.fail_projectile_tag, tree)

            elif tag_header.tag_type == 'mode':
                model = myth_tags.parse_model(tag_data)
                yield from self.get_tag_data('geom', model.geometry_tag, tree)

            elif tag_header.tag_type == 'geom':
                model = myth_tags.parse_geom(tag_data)
                yield from self.get_tag_data('core', model.collection_reference_tag, tree)

            elif tag_header.tag_type == 'mons':
                mons = mons_tag.parse_tag(tag_data)
                yield from self.get_tag_data('.256', mons.collection_tag, tree)
                yield from self.get_tag_data('prgr', mons.burning_death_projectile_group_tag, tree)
                yield from self.get_tag_data('obje', mons.object_tag, tree)
                yield from self.get_tag_data('prgr', mons.exploding_projectile_group_tag, tree)
                yield from self.get_tag_data('prgr', mons.melee_impact_projectile_group_tag, tree)
                yield from self.get_tag_data('prgr', mons.dying_projectile_group_tag, tree)
                yield from self.get_tag_data('stli', mons.spelling_string_list_tag, tree)
                yield from self.get_tag_data('stli', mons.names_string_list_tag, tree)
                yield from self.get_tag_data('stli', mons.flavor_string_list_tag, tree)
                yield from self.get_tag_data('prgr', mons.blocked_impact_projectile_group_tag, tree)
                yield from self.get_tag_data('prgr', mons.absorbed_impact_projectile_group_tag, tree)
                yield from self.get_tag_data('prgr', mons.ammunition_projectile_tag, tree)
                yield from self.get_tag_data('prgr', mons.entrance_projectile_group_tag, tree)
                yield from self.get_tag_data('lpgr', mons.local_projectile_group_tag, tree)
                yield from self.get_tag_data('stli', mons.special_ability_string_list_tag, tree)
                yield from self.get_tag_data('prgr', mons.exit_projectile_group_tag, tree)
                yield from self.get_tag_data('prgr', mons.initial_artifacts_projectile_group_tag, tree)
                for sound in mons.sound_tags:
                    if sound:
                        yield from self.get_tag_data('soun', sound, tree)
                for attack in mons.attacks:
                    if attack:
                        yield from self.get_tag_data('proj', attack.projectile_tag, tree)

            elif tag_header.tag_type == 'anim':
                anim = myth_tags.parse_anim(tag_data)
                yield from self.get_tag_data('soun', anim.forward_sound_tag, tree)
                yield from self.get_tag_data('soun', anim.backward_sound_tag, tree)
                for frame in anim.frames:
                    yield from self.get_tag_data('mode', frame.model_tag, tree)

            elif tag_header.tag_type == 'scen':
                scenery = myth_tags.parse_scenery(tag_data)
                yield from self.get_tag_data('core', scenery.collection_reference_tag, tree)
                yield from self.get_tag_data('obje', scenery.object_tag, tree)
                yield from self.get_tag_data('proj', scenery.projectile_tag, tree)
                for scen_prgr in scenery.projectile_group_tags:
                    yield from self.get_tag_data('prgr', scen_prgr, tree)

            elif tag_header.tag_type == 'proj':
                proj = myth_projectile.parse_proj(tag_data)
                yield from self.get_tag_data('.256', proj.collection_tag, tree)
                yield from self.get_tag_data('prgr', proj.detonation_projectile_group_tag, tree)
                yield from self.get_tag_data('proj', proj.contrail_projectile_tag, tree)
                yield from self.get_tag_data('obje', proj.object_tag, tree)
                yield from self.get_tag_data('ligh', proj.lightning_tag, tree)
                yield from self.get_tag_data('soun', proj.flight_sound_tag, tree)
                yield from self.get_tag_data('soun', proj.rebound_sound_tag, tree)
                yield from self.get_tag_data('soun', proj.sound_tag_3, tree)
                yield from self.get_tag_data('soun', proj.sound_tag_4, tree)
                yield from self.get_tag_data('proj', proj.promoted_projectile_tag, tree)
                yield from self.get_tag_data('prgr', proj.promotion_projectile_group_tag, tree)
                yield from self.get_tag_data('arti', proj.artifact_tag, tree)
                yield from self.get_tag_data('prgr', proj.target_detonation_projectile_group_tag, tree)
                yield from self.get_tag_data('geom', proj.geometry_tag, tree)
                yield from self.get_tag_data('lpgr', proj.local_projectile_group_tag, tree)
                yield from self.get_tag_data('unit', proj.promotion_unit_tag, tree)

            elif tag_header.tag_type == 'arti':
                artifact = mons_tag.parse_artifact(tag_data)
                # yield from self.get_tag_data('mons', artifact.monster_restriction_tag, tree)
                yield from self.get_tag_data('.256', artifact.collection_tag, tree)
                yield from self.get_tag_data('proj', artifact.override_attack.projectile_tag, tree)
                yield from self.get_tag_data('stli', artifact.special_ability_string_list_tag, tree)
                yield from self.get_tag_data('mons', artifact.monster_override_tag, tree)
                for arti_proj in artifact.projectile_tags:
                    yield from self.get_tag_data('proj', arti_proj, tree)

            elif tag_header.tag_type == '.256':
                coll_header = myth_collection.parse_collection_header(tag_data, tag_header)
                sequences = myth_collection.parse_sequences(tag_data, coll_header)
                for seq in sequences:
                    yield from self.get_tag_data('soun', seq['metadata'].sound_tag_first, tree)
                    yield from self.get_tag_data('soun', seq['metadata'].sound_tag_key, tree)
                    yield from self.get_tag_data('soun', seq['metadata'].sound_tag_last, tree)

            elif tag_header.tag_type == 'ligh':
                lightning = myth_projectile.parse_lightning(tag_data)
                yield from self.get_tag_data('core', lightning.collection_reference_tag, tree)

            if not self.plugin_names or location in self.plugin_names:
                tree_path = ' > '.join([
                    f'{tree_header.tag_type.upper()}.{tree_header.tag_id}'
                    for (tree_loc, tree_header) in tree
                ])
                if DEBUG:
                    print(f'{location:<32} {tag_type.upper()}.{tag_header.tag_id} {tag_header.name:<32} {tree_path}')
                yield (tag_header, tag_data)

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
        main(game_directory, tag_type.lower(), tag_id.lower(), plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
