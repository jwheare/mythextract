#!/usr/bin/env python3
from collections import OrderedDict
import enum
import os
import struct

import codec
import myth_headers

DEBUG = (os.environ.get('DEBUG') == '1')
DEBUG_ACTIONS = (os.environ.get('DEBUG_ACTIONS') == '1')
DEBUG_MARKERS = (os.environ.get('DEBUG_MARKERS') == '1')

MESH_HEADER_SIZE = 1024
ACTION_HEAD_SIZE = 64
WORLD_POINT_SF = 512
FIXED_SF = 1 << 16
ANGLE_SF = FIXED_SF / 360
TIME_SF = 30

# 887E <- action_id
# 0000 <- expiration_mode
# 61636C69 <- action_type
# 0000 0001 <- flags
# 0000 0000 <- trigger_time_lower_bound
# 0000 0000 <- trigger_time_delta
# 0002 <- num_params
# 002C <- size
# 0000 320C <- offset
# 0000 <- indent
# unused
# 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000

class ActionExpiration(enum.Enum):
    TRIGGER = 0
    EXECUTION = enum.auto()
    SUCCESSFUL_EXECUTION = enum.auto()
    NEVER = enum.auto()
    FAILED_EXECUTION = enum.auto()

class ActionFlag(enum.Flag):
    INITIALLY_ACTIVE = enum.auto()
    ACTIVATES_ONLY_ONCE = enum.auto()
    NO_INITIAL_DELAY = enum.auto()
    ONLY_INITIAL_DELAY = enum.auto()
    DELETED_ON_DEACTIVATION = enum.auto()

ActionHeadFmt = ('ActionHead', [
    ('H', 'id'),
    ('H', 'expiration_mode', ActionExpiration),
    ('4s', 'type', codec.decode_string_none, codec.encode_string_none),
    ('L', 'flags', ActionFlag),
    ('L', 'trigger_time_lower_bound', TIME_SF),
    ('L', 'trigger_time_delta', TIME_SF),
    ('H', 'num_params'),
    ('H', 'size'),
    ('L', 'offset'),
    ('H', 'indent'),
    ('34x', None),
])

class MeshFlags(enum.Flag, boundary=enum.CONFORM):
    BODY_COUNT = enum.auto()
    STEAL_THE_BACON = enum.auto()
    LAST_MAN_ON_THE_HILL = enum.auto()
    SCAVENGER_HUNT = enum.auto()
    FLAG_RALLY = enum.auto()
    CAPTURE_THE_FLAG = enum.auto()
    BALLS_ON_PARADE = enum.auto()
    TERRITORIES = enum.auto()
    CAPTURES = enum.auto()
    KING_OF_THE_HILL = enum.auto()
    STAMPEDE = enum.auto()
    ASSASSIN = enum.auto()
    HUNTING = enum.auto()
    CUSTOM = enum.auto()
    KING_OF_THE_HILL_TFL = enum.auto() # Currently non functional?
    KING_OF_THE_MAP = enum.auto() # Currently non functional?
    SINGLE_PLAYER_MAP = enum.auto()
    SUPPORTS_UNIT_TRADING = enum.auto()
    SUPPORTS_VETERANS = enum.auto()
    HAS_LIMITED_TERRAIN_VISIBILITY = enum.auto()
    IS_COMPLETE = enum.auto()
    CAN_BE_USED_BY_DEMO = enum.auto()
    LEAVES_OVERHEAD_MAP_CLOSED = enum.auto()
    IS_TRAINING_MAP = enum.auto()
    CAN_CATCH_FIRE = enum.auto()
    HAS_CEILING = enum.auto()
    HAS_TERRAIN_FOLLOWING_CAMERA = enum.auto()
    OVERHEAD_MAP_DOESNT_SCROLL = enum.auto()
    MODELS_DONT_LIMIT_RENDERING = enum.auto()
    USES_ANTICLUMP = enum.auto()
    USES_VTFL = enum.auto()
    REQUIRES_PLUGIN = enum.auto()

class ExtraFlags(enum.Flag):
    LAST_LEVEL = enum.auto()
    PREGAME_CUTSCENE_BEFORE_NARRATION = enum.auto()
    PREGAME_CUTSCENE_AFTER_NARRATION = enum.auto()
    SECRET_LEVEL = enum.auto()

MeshHeaderFmt = ('MeshHeader', [
    ('4s', 'landscape_collection_tag'),
    ('4s', 'media_tag'),
    ('H', 'submesh_width'),
    ('H', 'submesh_height'),
    ('L', 'mesh_offset'),
    ('L', 'mesh_size'),
    ('4x', None), # runtime: mesh_ptr
    ('L', 'data_offset'),
    ('L', 'data_size'),
    ('4x', None), # runtime: data_ptr
    ('L', 'marker_palette_entries'),
    ('L', 'marker_palette_offset'),
    ('L', 'marker_palette_size'),
    ('4x', None), # runtime: marker_palette_ptr
    ('L', 'marker_count'),
    ('L', 'markers_offset'),
    ('L', 'markers_size'),
    ('4x', None), # runtime: markers_ptr
    ('4s', 'mesh_lighting_tag'),
    ('4s', 'connector_tag'),
    ('L', 'flags', MeshFlags),
    ('4s', 'particle_system_tag'),
    ('l', 'team_count'),
    ('h', 'dark_fraction'),
    ('h', 'light_fraction'),
    ('8s', 'dark_color'),
    ('8s', 'light_color'),
    ('l', 'transition_point'),
    ('h', 'ceiling_height'),
    ('B', 'min_vtfl_version'),
    ('B', 'max_vtfl_version'),
    ('8s', 'edge_of_mesh_buffer_zones'),
    ('4s', 'global_ambient_sound_tag'),
    ('L', 'map_action_count'),
    ('L', 'map_actions_offset'),
    ('L', 'map_action_buffer_size'),
    ('4s', 'map_description_string_list_tag'),
    ('4s', 'postgame_collection_tag'),
    ('4s', 'pregame_collection_tag'),
    ('4s', 'overhead_map_collection_tag'),
    ('4s', 'next_mesh'),
    ('4s', 'next_mesh_alternate'),
    ('4s', 'cutscene_tag_pregame'),
    ('4s', 'cutscene_tag_success'),
    ('4s', 'cutscene_tag_failure'),
    ('4s', 'pregame_storyline_tag'),
    ('4s', 'storyline_string_tags_2'),
    ('4s', 'storyline_string_tags_3'),
    ('4s', 'storyline_string_tags_4'),
    ('L', 'media_coverage_region_offset'),
    ('L', 'media_coverage_region_size'),
    ('4x', None), # runtime: media_coverage_region_ptr
    ('L', 'mesh_LOD_data_offset'),
    ('L', 'mesh_LOD_data_size'),
    ('4x', None), # runtime: mesh_LOD_data_ptr
    ('8s', 'global_tint_color'),
    ('h', 'global_tint_fraction'),
    ('H', 'pad'),
    ('4s', 'wind_tag'),
    ('4s', 'screen_collection_tags_1'),
    ('4s', 'screen_collection_tags_2'),
    ('4s', 'screen_collection_tags_3'),
    ('8s', 'blood_color'),
    ('4s', 'picture_caption_string_list_tag'),
    ('4s', 'narration_sound_tag'),
    ('4s', 'win_ambient_sound_tag'),
    ('4s', 'loss_ambient_sound_tag'),
    ('L', 'reverb_environment'),
    ('f', 'reverb_volume'),
    ('f', 'reverb_decay_time'),
    ('f', 'reverb_damping'),
    ('L', 'connector_count'),
    ('L', 'connectors_offset'),
    ('L', 'connectors_size'),
    ('4x', None), # runtime: connectors_ptr
    ('64s', 'cutscene_file_pregame', codec.String),
    ('64s', 'cutscene_file_success', codec.String),
    ('64s', 'cutscene_file_failure', codec.String),
    ('4s', 'hints_string_list_tag'),
    ('8s', 'fog_color'),
    ('f', 'fog_density'),
    ('4s', 'difficulty_level_override_string_list_tag'),
    ('4s', 'team_names_override_string_list_tag'),
    ('32s', 'plugin_name'),
    ('L', 'extra_flags', ExtraFlags),
    ('f', 'minimum_zoom_factor'),
    ('468x', None),
])

# nested tags
# connector_tag       [conn] -> .256
# media_tag           [medi] -> core -> .256
# media_tag           [medi] -> lpgr -> .256/phys
# media_tag           [medi] -> prgr -> meef/soun/lpgr/proj
# particle_system_tag [part] -> core -> .256
# particle_system_tag [part] -> lpgr

# markers with nested tags
# MarkerType.SCENERY
#     [scen] -> core -> .256
#     [scen] -> proj
#     [scen] -> obje
#     [scen] -> lpgr
# MarkerType.UNIT
#     [unit] -> core -> .256
#     [unit] -> mons ->
#         lpgr
#         obje
#         prgr
#         proj
#         soun
#         stli
# MarkerType.AMBIENT_SOUND
#     [amso] -> soun
# MarkerType.MODEL
#     [mode] -> geom -> core -> .256
# MarkerType.PROJECTILE
#     [proj] ->
#         .256
#         arti
#         geom
#         ligh
#         lpgr
#         obje
#         prgr
#         proj
#         soun
#         unit
# MarkerType.LOCAL_PROJECTILE_GROUP
#     [lpgr] -> .256
#     [lpgr] -> phys
# MarkerType.ANIMATION
#     [anim] -> mode -> geom -> core -> .256
#     [anim] -> soun

class MarkerType(enum.Enum):
    OBSERVER = 0
    SCENERY = enum.auto()
    UNKNOWN_1 = enum.auto()
    UNIT = enum.auto()
    UNKNOWN_2 = enum.auto()
    AMBIENT_SOUND = enum.auto()
    MODEL = enum.auto()
    UNKNOWN_3 = enum.auto()
    UNKNOWN_4 = enum.auto()
    PROJECTILE = enum.auto()
    LOCAL_PROJECTILE_GROUP = enum.auto()
    ANIMATION = enum.auto()
Marker2Tag = {
    MarkerType.SCENERY: 'scen',
    MarkerType.UNIT: 'unit',
    MarkerType.AMBIENT_SOUND: 'amso',
    MarkerType.MODEL: 'mode',
    MarkerType.PROJECTILE: 'proj',
    MarkerType.LOCAL_PROJECTILE_GROUP: 'lpgr',
    MarkerType.ANIMATION: 'anim',
}
def param_id_marker(param_type, param_name):
    if param_type == ParamType.MONSTER_IDENTIFIER:
        return MarkerType.UNIT
    if param_type == ParamType.SOUND_SOURCE_IDENTIFIER:
        return MarkerType.AMBIENT_SOUND
    if param_type == ParamType.OBJECT_IDENTIFIER:
        return MarkerType.PROJECTILE
    if param_type == ParamType.MODEL_IDENTIFIER:
        return MarkerType.MODEL
    if param_type == ParamType.LOCAL_PROJECTILE_GROUP_IDENTIFIER:
        return MarkerType.LOCAL_PROJECTILE_GROUP
    if param_type == ParamType.MODEL_ANIMATION_IDENTIFIER:
        return MarkerType.ANIMATION

class MarkerPaletteFlag(enum.Flag, boundary=enum.CONFORM):
    UNCONTROLLABLE = enum.auto()
    MAY_BE_TRADED = enum.auto()
    MAY_USE_VETERANS = enum.auto()
    MUST_USE_VETERANS = enum.auto()
    AMBIENT_LIFE = enum.auto()
    HUNTED_CREATURE = enum.auto()
MarkerPalleteFlagInfo = {
    MarkerPaletteFlag.UNCONTROLLABLE: 'uncontrollable',
    MarkerPaletteFlag.MAY_BE_TRADED: 'can_trade',
    MarkerPaletteFlag.MAY_USE_VETERANS: 'can_vet',
    MarkerPaletteFlag.MUST_USE_VETERANS: 'must_vet',
    MarkerPaletteFlag.AMBIENT_LIFE: 'ambient',
    MarkerPaletteFlag.HUNTED_CREATURE: 'hunted',
}
def palette_flag_info(flag):
    return [info for f, info in MarkerPalleteFlagInfo.items() if f in flag]

class NetgameFlag(enum.Flag, boundary=enum.CONFORM):
    BODY_COUNT = enum.auto()
    STEAL_THE_BACON = enum.auto()
    LAST_MAN_ON_THE_HILL = enum.auto()
    SCAVENGER_HUNT = enum.auto()
    FLAG_RALLY = enum.auto()
    CAPTURE_THE_FLAG = enum.auto()
    BALLS_ON_PARADE = enum.auto()
    TERRITORIES = enum.auto()
    CAPTURES = enum.auto()
    KING_OF_THE_HILL = enum.auto()
    STAMPEDE = enum.auto()
    ASSASSIN = enum.auto()
    HUNTING = enum.auto()
    CUSTOM = enum.auto()
    KING_OF_THE_HILL_TFL = enum.auto()
    KING_OF_THE_MAP = enum.auto()
NetgameFlagInfo = OrderedDict({
    NetgameFlag.BODY_COUNT: 'bc',
    NetgameFlag.STEAL_THE_BACON: 'stb',
    NetgameFlag.LAST_MAN_ON_THE_HILL: 'lmoth',
    NetgameFlag.SCAVENGER_HUNT: 'scav',
    NetgameFlag.FLAG_RALLY: 'fr',
    NetgameFlag.CAPTURE_THE_FLAG: 'ctf',
    NetgameFlag.BALLS_ON_PARADE: 'balls',
    NetgameFlag.TERRITORIES: 'terries',
    NetgameFlag.CAPTURES: 'caps',
    NetgameFlag.KING_OF_THE_HILL: 'koth',
    NetgameFlag.STAMPEDE: 'stamp',
    NetgameFlag.ASSASSIN: 'ass',
    NetgameFlag.HUNTING: 'hunt',
    NetgameFlag.CUSTOM: 'custom',
    NetgameFlag.KING_OF_THE_HILL_TFL: 'koth_tfl',
    NetgameFlag.KING_OF_THE_MAP: 'kotm',
})

def netgame_flag_info(flag):
    actual_flag = flag
    # These flags don't work, we just use the terries and koth_tfl values
    actual_flag &= ~(NetgameFlag.KING_OF_THE_MAP | NetgameFlag.KING_OF_THE_HILL_TFL)
    if NetgameFlag.TERRITORIES in flag:
        actual_flag |= NetgameFlag.KING_OF_THE_MAP
    if NetgameFlag.KING_OF_THE_HILL in flag:
        actual_flag |= NetgameFlag.KING_OF_THE_HILL_TFL

    if all([f in actual_flag for f in list(NetgameFlag)]):
        return ['all']
    else:
        return [info for f, info in NetgameFlagInfo.items() if f in actual_flag]

class MarkerFlag(enum.Flag):
    IS_INVISIBLE = enum.auto()
    IS_STONE = enum.auto()
    DETONATES_IMMEDIATELY = enum.auto()
    IS_INVISIBLE_OBSERVER = enum.auto()
    IS_NETGAME_TARGET = enum.auto()
    RESPAWNS = enum.auto()
    MANUAL_RESPAWN = enum.auto()
    REMEMBERS_LOCATION = enum.auto()
    USES_MONSTER_ENTRANCE = enum.auto()
MarkerFlagInfo = {
    MarkerFlag.IS_INVISIBLE: 'invis',
    MarkerFlag.IS_STONE: 'stone',
    MarkerFlag.DETONATES_IMMEDIATELY: 'detonates',
    MarkerFlag.IS_INVISIBLE_OBSERVER: 'invis_obs',
    MarkerFlag.IS_NETGAME_TARGET: 'netgame_targ',
    MarkerFlag.RESPAWNS: 'respawns',
    MarkerFlag.MANUAL_RESPAWN: 'respawns_manual',
    MarkerFlag.REMEMBERS_LOCATION: 'respawns_at_death_loc',
    MarkerFlag.USES_MONSTER_ENTRANCE: 'monster_entrance',
}
def marker_flag_info(flag):
    return [info for f, info in MarkerFlagInfo.items() if f in flag]

# 00000000 0003 0002 28DD(10461) 0000 0000BC4A(48202) 00008CB9(36025) 000005B7(1463)
#                    m_id           posx            posy            posz
# [8x00] 0000(00000) 0000 0000 [20x00] 0000        06EA(i=1770) 7916(30998)
#        yaw angle (/182.05)           player_idx  data_idx       data_id
MarkerHeadFmt = ('MarkerHead', [
    ('L', 'flags', MarkerFlag),
    ('H', 'type', MarkerType),
    ('H', 'palette_index'),
    ('H', 'id'),
    ('H', 'min_difficulty'),
    ('L', 'pos_x', WORLD_POINT_SF),
    ('L', 'pos_y', WORLD_POINT_SF),
    ('l', 'pos_z', WORLD_POINT_SF),
    ('8x', None),
    ('H', 'yaw', ANGLE_SF),
    ('2x', None),
    ('2x', None),
    ('20x', None),
    ('6x', None),
])

# type flag tag             team pad  netgame_flags unused_flags  unused                   runtime
# 0003 0004 64776172 [dwar] 0000 0000 0000          FFFF          0000 0000 0000 0000 0000 0000 0002  0000
MarkerPaletteEntryFmt = ('MarkerPaletteEntry', [
    ('H', 'type', MarkerType),
    ('H', 'flags', MarkerPaletteFlag),
    ('4s', 'marker_tag'),
    ('h', 'team_index'),
    ('2x', None),
    ('L', 'netgame_flags', NetgameFlag),
    ('10x', None),
    ('6x', None),
])

class ParamType(enum.Enum):
    FLAG = 0
    STRING = enum.auto()
    MONSTER_IDENTIFIER = enum.auto()
    ACTION_IDENTIFIER = enum.auto()
    ANGLE = enum.auto()
    INTEGER = enum.auto()
    WORLD_DISTANCE = enum.auto()
    FIELD_NAME = enum.auto()
    FIXED = enum.auto()
    PROJECTILE = enum.auto()
    STRING_LIST = enum.auto()
    SOUND = enum.auto()
    PROJECTILE_OR_WORLD_POINT_2D = enum.auto() # TFL = WORLD_POINT_2D / SB = PROJECTILE
    WORLD_POINT_2D = enum.auto()
    WORLD_RECTANGLE_2D = enum.auto()
    OBJECT_IDENTIFIER = enum.auto()
    MODEL_IDENTIFIER = enum.auto()
    SOUND_SOURCE_IDENTIFIER = enum.auto()
    WORLD_POINT_3D = enum.auto()
    LOCAL_PROJECTILE_GROUP_IDENTIFIER = enum.auto()
    MODEL_ANIMATION_IDENTIFIER = enum.auto()

Difficulty = [
    'Timid',
    'Simple',
    'Normal',
    'Heroic',
    'Legendary',
]

def difficulty(diff):
    return Difficulty[diff]

def align(align_bytes, value):
    return (value + (align_bytes-1)) & (align_bytes * -1)

def parse_header(data):
    return myth_headers.parse_tag(MeshHeaderFmt, data)

def required_plugin(mesh_header):
    if MeshFlags.REQUIRES_PLUGIN in mesh_header.flags and mesh_header.plugin_name:
        return mesh_header.plugin_name

def has_single_player_story(game_version, data):
    if not data:
        return False
    mesh_header = parse_header(data)
    # Long awaited party in TFL isn't marked as single player (secret)
    if game_version == 1 and mesh_header.pregame_storyline_tag == b'18al':
        return True
    if not is_single_player(mesh_header):
        return False
    if codec.all_on(mesh_header.pregame_storyline_tag):
        return False
    return True

def is_single_player(header):
    return MeshFlags.SINGLE_PLAYER_MAP in header.flags

def is_vtfl(header):
    return MeshFlags.USES_VTFL in header.flags

def cutscenes(game_version, header):
    return (
        codec.decode_string(header.cutscene_file_pregame),
        codec.decode_string(header.cutscene_file_success)
    )

def get_offset(offset):
    return myth_headers.TAG_HEADER_SIZE + MESH_HEADER_SIZE + offset

def parse_palette_entry(entry):
    return {
        'flags': entry.flags,
        'type': entry.type,
        'tag': codec.String(entry.marker_tag),
        'team_index': entry.team_index,
        'netgame_flags': entry.netgame_flags,
        'markers': {},
    }

# Not scientific, could be tweaked
def mesh_size(mesh_header):
    if mesh_header.mesh_size < 440000:
        return 'small'
    elif mesh_header.mesh_size < 500000:
        return 'medium'
    else:
        return 'large'

def parse_markers(mesh_header, data):
    marker_palette_start = get_offset(mesh_header.marker_palette_offset)
    marker_palette_end = marker_palette_start + mesh_header.marker_palette_size
    marker_palette_data = data[marker_palette_start:marker_palette_end]

    palette = {}
    orphans = {
        'markers': {},
        'count': 0,
    }
    for entry in codec.iter_decode(
        0, mesh_header.marker_palette_entries,
        MarkerPaletteEntryFmt, marker_palette_data
    ):
        entry_dict = parse_palette_entry(entry)
        palette_list = palette.get(entry_dict['type'], [])
        palette_list.append(entry_dict)
        palette[entry_dict['type']] = palette_list

    if DEBUG_MARKERS:
        print('Palette')
        for m_type, type_palette in palette.items():
            print(m_type, len(type_palette))
            # for palette_entry in type_palette:
            #     print(palette_entry['tag'])

    marker_start = get_offset(mesh_header.markers_offset)
    marker_end = marker_start + mesh_header.markers_size
    marker_data = data[marker_start:marker_end]

    for mhead in codec.iter_decode(
        0, mesh_header.marker_count,
        MarkerHeadFmt, marker_data
    ):
        (marker, palette_item) = parse_marker_head(mhead, palette)
        if palette_item:
            palette_item['markers'][marker['marker_id']] = marker
        else:
            if marker['type'] not in orphans['markers']:
                orphans['markers'][marker['type']] = {}
            orphans['markers'][marker['type']][marker['marker_id']] = marker
            orphans['count'] = orphans['count'] + 1

    return (palette, orphans)

def parse_marker_head(mhead, palette):
    palette_item = None
    if (mhead.type in palette) and (mhead.palette_index < len(palette[mhead.type])):
        palette_item = palette[mhead.type][mhead.palette_index]

    marker = {
        'marker_id': mhead.id,
        'type': mhead.type,
        'palette_index': mhead.palette_index,
        'tag': palette_item['tag'] if palette_item else None,
        'flags': mhead.flags,
        'min_difficulty': mhead.min_difficulty,
        'facing': mhead.yaw,
        'pos': (mhead.pos_x, mhead.pos_y, mhead.pos_z)
    }
    return (marker, palette_item)

def encode_map_action_param(game_version, param):
    param_type = param['type']
    param_elems = param['elements']
    num_elems = len(param_elems)

    if param_type == ParamType.STRING:
        string_enc = codec.encode_string(param_elems[0])
        elem_count = len(string_enc) + 1
        align_string_len = align(4, elem_count)
        elem_struct = f'{align_string_len}s'
        elem_values = [codec.encode_string(param_elems[0])]
    elif param_type in [ParamType.SOUND, ParamType.FIELD_NAME, ParamType.PROJECTILE]:
        elem_count = num_elems
        elem_struct = num_elems * '4s'
        elem_values = [codec.encode_string(elem) for elem in param_elems]
    elif param_type == ParamType.WORLD_POINT_2D:
        elem_count = num_elems
        elem_struct = f'{num_elems * 2}L'
        elem_values = [round(val * WORLD_POINT_SF) for pair in param_elems for val in pair]
    elif param_type == ParamType.WORLD_POINT_3D:
        elem_count = num_elems
        elem_struct = f'{num_elems * 3}L'
        elem_values = [round(val * WORLD_POINT_SF) for pair in param_elems for val in pair]
    elif param_type == ParamType.FIXED:
        elem_count = num_elems
        elem_struct = f'{num_elems}L'
        elem_values = [round(val * FIXED_SF) for val in param_elems]
    elif param_type == ParamType.INTEGER:
        elem_count = num_elems
        elem_struct = f'{num_elems}l'
        elem_values = param_elems
    elif param_type == ParamType.WORLD_DISTANCE:
        elem_count = num_elems
        elem_struct = f'{num_elems}L'
        elem_values = [round(val * WORLD_POINT_SF) for val in param_elems]
    elif param_type == ParamType.FLAG:
        elem_count = num_elems
        align_struct_len = align(4, num_elems)
        num_pad = align_struct_len - num_elems
        elem_struct = f'{num_elems}?{num_pad}x'
        elem_values = param_elems
    else:
        if param_type == ParamType.ANGLE:
            elem_values = [round(val * ANGLE_SF) for val in param_elems]
        else:
            elem_values = param_elems
        elem_count = num_elems
        align_struct_len = align(2, num_elems)
        num_pad = align_struct_len - num_elems
        elem_struct = f'{num_elems}H{2 * num_pad}x'

    return struct.pack(
        f'>H H 4s {elem_struct}',
        param_type.value, elem_count, codec.encode_string(param['name']),
        *elem_values
    )

def encode_map_action_data(game_version, actions):
    action_data = b''
    all_param_data = b''
    param_offset = 0
    for action_id, action in actions.items():
        param_data = b''
        num_params = len(action['parameters'])
        if action['name']:
            param_data += encode_map_action_param(game_version, {
                'type': ParamType.STRING,
                'name': 'name',
                'elements': [action['name']]
            })
            num_params += 1
        for param in action['parameters']:
            param_data += encode_map_action_param(game_version, param)

        action_type = codec.encode_string_none(action['type'])

        action_data += codec.encode_data(
            ActionHeadFmt,
            (
                action_id,
                action['expiration_mode'],
                action_type,
                action['flags'],
                action['trigger_time_lower_bound'],
                action['trigger_time_delta'],
                num_params,
                len(param_data),
                param_offset,
                action['indent']
            )
        )
        all_param_data += param_data

        param_offset = param_offset + len(param_data)
    return (len(actions), action_data + all_param_data)

def rewrite_action_data(map_action_count, map_action_data, current_mesh_tag_data):
    mesh_header = parse_header(current_mesh_tag_data)
    tag_header = myth_headers.parse_header(current_mesh_tag_data)

    # Insert new action data into current data
    current_action_start = get_offset(mesh_header.map_actions_offset)
    current_action_end = current_action_start + mesh_header.map_action_buffer_size
    new_mesh_data = (
        current_mesh_tag_data[get_offset(0):current_action_start]
        + map_action_data
        + current_mesh_tag_data[current_action_end:]
    )
    mesh_data_size = len(new_mesh_data)

    # Adjust sizes and offsets
    map_action_buffer_size = len(map_action_data)
    map_action_size_diff = map_action_buffer_size - mesh_header.map_action_buffer_size

    media_coverage_region_offset = mesh_header.media_coverage_region_offset + map_action_size_diff
    mesh_LOD_data_offset = mesh_header.mesh_LOD_data_offset + map_action_size_diff
    connectors_offset = mesh_header.connectors_offset + map_action_size_diff

    new_mesh_header = mesh_header._replace(
        data_size=mesh_data_size,
        map_action_count=map_action_count,
        map_action_buffer_size=map_action_buffer_size,
        media_coverage_region_offset=media_coverage_region_offset,
        mesh_LOD_data_offset=mesh_LOD_data_offset,
        connectors_offset=connectors_offset,
    )
    new_mesh_header_data = new_mesh_header.value
    new_mesh_header_size = len(new_mesh_header_data)
    new_tag_data_size = new_mesh_header_size + mesh_data_size

    # Adjust tag header size
    new_tag_header = myth_headers.normalise_tag_header(
        tag_header,
        tag_data_size=new_tag_data_size
    )

    if DEBUG:
        print(
            f"""Updated tag values
                tag_header.tag_data_size = {tag_header.tag_data_size} -> {new_tag_header.tag_data_size}
                   mesh_header.data_size = {mesh_header.data_size} -> {new_mesh_header.data_size}
      mesh_header.map_action_buffer_size = {mesh_header.map_action_buffer_size} -> {new_mesh_header.map_action_buffer_size}
mesh_header.media_coverage_region_offset = {mesh_header.media_coverage_region_offset} -> {new_mesh_header.media_coverage_region_offset}
        mesh_header.mesh_LOD_data_offset = {mesh_header.mesh_LOD_data_offset} -> {new_mesh_header.mesh_LOD_data_offset}
           mesh_header.connectors_offset = {mesh_header.connectors_offset} -> {new_mesh_header.connectors_offset}"""
        )

    return (
        new_tag_header.value
        + new_mesh_header_data
        + new_mesh_data
    )

def encode_map_actions(mesh_tag_data, actions):
    tag_header = myth_headers.parse_header(mesh_tag_data)
    (map_action_count, map_action_data) = encode_map_action_data(myth_headers.game_version(tag_header), actions)
    return rewrite_action_data(map_action_count, map_action_data, mesh_tag_data)

def parse_map_actions(mesh_header, data):
    tag_header = myth_headers.parse_header(data)
    game_version = myth_headers.game_version(tag_header)
    map_action_start = get_offset(mesh_header.map_actions_offset)
    map_action_end = map_action_start + mesh_header.map_action_buffer_size
    map_action_data = data[map_action_start:map_action_end]

    num_actions = mesh_header.map_action_count

    action_head_end = num_actions * ACTION_HEAD_SIZE
    action_data_end = 0
    ends = [0]
    actions = OrderedDict()
    for action_head in codec.iter_decode(
        0, num_actions,
        ActionHeadFmt, map_action_data
    ):
        action_data_start = action_head_end + action_head.offset
        action_data_end = action_data_start + action_head.size
        action_data = map_action_data[action_data_start:action_data_end]

        param_remain = action_head.num_params
        param_start = 0
        name = ''
        parameters = []
        while param_remain:
            param_head_end = param_start + 8
            param_head_data = action_data[param_start:param_head_end]
            
            (param_type, num_elems, param_name) = struct.unpack(">H H 4s", param_head_data)

            param_name = codec.decode_string(param_name)

            if DEBUG_ACTIONS:
                print(action_head.id, action_head.type, param_head_data.hex(), param_name, param_type, end=' ')

            param_type = ParamType(param_type)
            scale_factor = None

            tfl = (game_version == 1)
            if param_type == ParamType.PROJECTILE_OR_WORLD_POINT_2D:
                param_type = ParamType.WORLD_POINT_2D if tfl else ParamType.PROJECTILE
            if tfl and param_type == ParamType.WORLD_RECTANGLE_2D:
                param_type = ParamType.OBJECT_IDENTIFIER
            if tfl and param_type == ParamType.MODEL_IDENTIFIER:
                param_type = ParamType.SOUND_SOURCE_IDENTIFIER
            if tfl and param_type == ParamType.WORLD_POINT_3D:
                param_type = ParamType.LOCAL_PROJECTILE_GROUP_IDENTIFIER

            if param_type == ParamType.STRING:
                align_num_elems = align(4, num_elems)
                param_bytes = align_num_elems
                param_struct = f'{align_num_elems}s'
            elif param_type in [ParamType.SOUND, ParamType.FIELD_NAME, ParamType.PROJECTILE]:
                param_bytes = num_elems * 4
                param_struct = num_elems * '4s'
            elif param_type == ParamType.WORLD_POINT_2D:
                num_elems = (num_elems * 2)
                param_bytes = num_elems * 4
                scale_factor = WORLD_POINT_SF
                param_struct = f'{num_elems}L'
            elif param_type == ParamType.WORLD_POINT_3D:
                num_elems = (num_elems * 3)
                param_bytes = num_elems * 4
                scale_factor = WORLD_POINT_SF
                param_struct = f'{num_elems}L'
            elif param_type == ParamType.FIXED:
                param_bytes = num_elems * 4
                scale_factor = FIXED_SF
                param_struct = f'{num_elems}L'
            elif param_type == ParamType.INTEGER:
                param_bytes = num_elems * 4
                param_struct = f'{num_elems}l'
            elif param_type == ParamType.WORLD_DISTANCE:
                param_bytes = num_elems * 4
                scale_factor = WORLD_POINT_SF
                param_struct = f'{num_elems}L'
            elif param_type == ParamType.FLAG:
                align_num_elems = align(4, num_elems)
                param_bytes = align_num_elems
                param_struct = f'{align_num_elems}?'
            else:
                if param_type == ParamType.ANGLE:
                    scale_factor = ANGLE_SF
                align_num_elems = align(2, num_elems)
                param_bytes = align_num_elems * 2
                param_struct = f'{align_num_elems}H'

            param_end = param_head_end + param_bytes
            param_data = action_data[param_head_end:param_end]
            param_fmt = f">{param_struct}"
            if DEBUG_ACTIONS:
                print(param_type, param_fmt, param_data.hex(), param_bytes, len(param_data))
            param_elems = struct.unpack(param_fmt, param_data)

            # Post process
            remainder = None
            if param_type == ParamType.STRING:
                remainder = param_elems[0][num_elems:]
                param_elems = codec.decode_string(param_elems[0][:num_elems])
            elif param_type in [ParamType.SOUND, ParamType.FIELD_NAME, ParamType.PROJECTILE]:
                remainder = param_elems[num_elems:]
                param_elems = [codec.decode_string(elem) for elem in param_elems[:num_elems]]
            elif param_type == ParamType.FLAG:
                # Only look at the first byte
                remainder = param_elems[1:]
                if len(param_elems):
                    param_elems = param_elems[0]
                else:
                    param_elems = True
            else:
                remainder = param_elems[num_elems:]
                param_elems = param_elems[:num_elems]

            if scale_factor:
                param_elems = [round(p / scale_factor, 4) for p in param_elems]

            if param_type == ParamType.WORLD_POINT_2D:
                world_points = []
                for i in range(0, len(param_elems), 2):
                    world_points.append((param_elems[i], param_elems[i+1]))
                param_elems = world_points

            if param_type == ParamType.WORLD_POINT_3D:
                world_points = []
                for i in range(0, len(param_elems), 3):
                    world_points.append((param_elems[i], param_elems[i+1], param_elems[i+2]))
                param_elems = world_points

            if DEBUG_ACTIONS:
                print(f'{param_remain:<3} \x1b[1m{param_type}\x1b[0m [{num_elems}] {param_elems} \x1b[1m{remainder}\x1b[0m', param_fmt, param_data.hex())

            if param_name == 'name':
                name = param_elems
            else:
                if hasattr(param_elems, '__iter__'):
                    param_elems = list(param_elems)
                else:
                    param_elems = [param_elems]

                parameters.append({
                    'type': param_type,
                    'name': param_name,
                    'elements': param_elems
                })

            param_start = param_end
            param_remain = param_remain - 1

        ends.append(action_data_end)

        actions[action_head.id] = {
            'type': action_head.type,
            'action_id': action_head.id,
            'expiration_mode': action_head.expiration_mode,
            'name': name,
            'flags': action_head.flags,
            'trigger_time_lower_bound': action_head.trigger_time_lower_bound,
            'trigger_time_delta': action_head.trigger_time_delta,
            'parameters': parameters,
            'indent': action_head.indent,
        }
    action_remainder = map_action_data[max(ends):]
    return (actions, action_remainder)
