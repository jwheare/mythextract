#!/usr/bin/env python3
from collections import namedtuple, OrderedDict
import enum
import struct

import myth_headers

MESH_HEADER_SIZE = 1024
ACTION_HEAD_SIZE = 64
PALETTE_SIZE = 32
MARKER_SIZE = 64
WORLD_POINT_SF = 512
# Weird, but matches exported actions
ANGLE_SF = (0xffff / 366) + 3
# This would make more sense
# (0xffff / 365)
MeshHeaderFmt = """>
    4s 4s
H H
L L L
L L L
L L L L
L L L L
4s 4s
L
4s
l
h h
8s
8s
l
h
H
8s
4s
L L L
4s
4s
4s
4s
4s 4s
4s 4s 4s
4s 4s 4s 4s
L L L
L L L
8s
h H
4s
4s 4s 4s
8s
4s 4s 4s 4s
L f f f
L L L L
64s 64s 64s
4s
8s
f
4s 4s
32s
446s
H
H
H
H
H
H
H
16s
"""
MeshHeader = namedtuple('MeshHeader', [
    'landscape_collection_tag', 'media_tag',
    'submesh_width', 'submesh_height',
    'mesh_offset', 'mesh_size', 'mesh_ptr',
    'data_offset', 'data_size', 'data_ptr',
    'marker_palette_entries', 'marker_palette_offset', 'marker_palette_size', 'marker_palette_ptr',
    'marker_count', 'markers_offset', 'markers_size', 'markers_ptr',
    'mesh_lighting_tag', 'connector_tag', 'flags', 'particle_system_tag',
    'team_count',
    'dark_fraction', 'light_fraction', 'dark_color', 'light_color',
    'transition_point', 'ceiling_height',
    'unused1',
    'edge_of_mesh_buffer_zones',
    'global_ambient_sound_tag',
    'map_action_count', 'map_actions_offset', 'map_action_buffer_size',
    'map_description_string_list_tag',
    'postgame_collection_tag',
    'pregame_collection_tag',
    'overhead_map_collection_tag',
    'next_mesh_tags_1', 'next_mesh_tags_2',
    'cutscene_movie_tags_1', 'cutscene_movie_tags_2', 'cutscene_movie_tags_3',
    'storyline_string_tags_1', 'storyline_string_tags_2',
    'storyline_string_tags_3', 'storyline_string_tags_4',
    'media_coverage_region_offset', 'media_coverage_region_size', 'media_coverage_region_ptr',
    'mesh_LOD_data_offset', 'mesh_LOD_data_size', 'mesh_LOD_data_ptr',
    'global_tint_color', 'global_tint_fraction',
    'pad',
    'wind_tag',
    'screen_collection_tags_1', 'screen_collection_tags_2', 'screen_collection_tags_3',
    'blood_color',
    'picture_caption_string_list_tag',
    'narration_sound_tag',
    'win_ambient_sound_tag',
    'loss_ambient_sound_tag',
    'reverb_environment', 'reverb_volume', 'reverb_decay_time', 'reverb_damping',
    'connector_count', 'connectors_offset', 'connectors_size', 'connectors_ptr',
    'cutscene_names_1', 'cutscene_names_2', 'cutscene_names_3',
    'hints_string_list_tag',
    'fog_color', 'fog_density',
    'difficulty_level_override_string_list_tag',
    'team_names_override_string_list_tag',
    'plugin_name',
    'unused',
    'connector_type',
    'map_description_string_index',
    'overhead_map_collection_index',
    'landscape_collection_index',
    'global_ambient_sound_index',
    'media_type',
    'hints_string_list_index',
    'editor_data',
])

class ActionFlag(enum.Flag):
    INITIALLY_ACTIVE = enum.auto()
    ACTIVATES_ONLY_ONCE = enum.auto()
    NO_INITIAL_DELAY = enum.auto()
    ONLY_INITIAL_DELAY = enum.auto()
    DELETED_ON_DEACTIVATION = enum.auto()

class ActionExpiration(enum.Enum):
    TRIGGER = 0
    EXECUTION = enum.auto()
    SUCCESSFUL_EXECUTION = enum.auto()
    NEVER = enum.auto()
    FAILED_EXECUTION = enum.auto()

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
    PROJECTILE2 = enum.auto()
    WORLD_POINT_2D = enum.auto()
    WORLD_RECTANGLE_2D = enum.auto()
    OBJECT_IDENTIFIER = enum.auto()
    MODEL_IDENTIFIER = enum.auto()
    SOUND_SOURCE_IDENTIFIER = enum.auto()
    WORLD_POINT_3D = enum.auto()
    LOCAL_PROJECTILE_GROUP_IDENTIFIER = enum.auto()
    MODEL_ANIMATION_IDENTIFIER = enum.auto()

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
    PROJECTILE_GROUP = enum.auto()
    ANIMATION = enum.auto()
Marker2Tag = {
    MarkerType.SCENERY: 'scen',
    MarkerType.UNIT: 'unit',
    MarkerType.AMBIENT_SOUND: 'amso',
    MarkerType.MODEL: 'mode',
    MarkerType.PROJECTILE: 'proj',
    MarkerType.PROJECTILE_GROUP: 'lpgr',
    MarkerType.ANIMATION: 'anim',
}

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
    ASSASSINATION = enum.auto()
    HUNTING = enum.auto()
    CUSTOM = enum.auto()
NetgameFlagInfo = {
    NetgameFlag.BODY_COUNT: 'bc',
    NetgameFlag.STEAL_THE_BACON: 'stb',
    NetgameFlag.LAST_MAN_ON_THE_HILL: 'lmoth',
    NetgameFlag.SCAVENGER_HUNT: 'scav',
    NetgameFlag.FLAG_RALLY: 'flag',
    NetgameFlag.CAPTURE_THE_FLAG: 'ctf',
    NetgameFlag.BALLS_ON_PARADE: 'balls',
    NetgameFlag.TERRITORIES: 'terries',
    NetgameFlag.CAPTURES: 'caps',
    NetgameFlag.KING_OF_THE_HILL: 'koth',
    NetgameFlag.STAMPEDE: 'stamp',
    NetgameFlag.ASSASSINATION: 'ass',
    NetgameFlag.HUNTING: 'hunt',
    NetgameFlag.CUSTOM: 'custom',
}
def netgame_flag_info(flag):
    if all([f in flag for f in list(NetgameFlag)]):
        return ['all']
    else:
        return [info for f, info in NetgameFlagInfo.items() if f in flag]

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
    mesh_header_start = myth_headers.TAG_HEADER_SIZE
    mesh_header_end = mesh_header_start + MESH_HEADER_SIZE
    return MeshHeader._make(
        struct.unpack(MeshHeaderFmt, data[mesh_header_start:mesh_header_end])
    )

def encode_header(header):
    return struct.pack(MeshHeaderFmt, *header)

def get_offset(offset):
    return myth_headers.TAG_HEADER_SIZE + MESH_HEADER_SIZE + offset

def parse_markers(mesh_header, data):
    marker_palette_start = get_offset(mesh_header.marker_palette_offset)
    marker_palette_end = marker_palette_start + mesh_header.marker_palette_size
    marker_palette_data = data[marker_palette_start:marker_palette_end]

    palette = {}
    orphans = {
        'markers': {},
        'count': 0,
    }
    palette_start = 0
    for i in range(mesh_header.marker_palette_entries):
        palette_end = palette_start + PALETTE_SIZE

        (
            p_type, p_flags, marker_tag, team_index, _, unused_flags, netgame_flags, _,
            # Don't rely on runtime values
            _player_index, _unreliable_count, _tag_index
        ) = struct.unpack(
            # type flag tag             team pad  netgame_flags unused_flags  unused                   runtime
            # 0003 0004 64776172 [dwar] 0000 0000 0000          FFFF          0000 0000 0000 0000 0000 0000 0002  0000
            """>
            H H
            4s
            h h
            H H
            10s

            H H H
            """,
            marker_palette_data[palette_start:palette_end]
        )
        marker_tag = myth_headers.decode_string(marker_tag)

        p_type = MarkerType(p_type)
        if p_type not in orphans['markers']:
            orphans['markers'][p_type] = {}
        palette_list = palette.get(p_type, [])
        palette[p_type] = palette_list
        palette_list.append({
            'idx': i,
            'flags': MarkerPaletteFlag(p_flags),
            'type': p_type,
            'tag': marker_tag,
            'team_index': team_index,
            'netgame_flags': NetgameFlag(netgame_flags),
            '_unreliable_count': _unreliable_count,
            'markers': {},
            'data': marker_palette_data[palette_start:palette_end]
        })

        palette_start = palette_end

    marker_start = get_offset(mesh_header.markers_offset)
    marker_end = marker_start + mesh_header.markers_size
    marker_data = data[marker_start:marker_end]

    m_start = 0
    for i in range(mesh_header.marker_count):
        m_end = m_start + MARKER_SIZE
        # 00000000 0003 0002 28DD(10461) 0000 0000BC4A(48202) 00008CB9(36025) 000005B7(1463)
        #                    m_id           posx            posy            posz
        # [8x00] 0000(00000) 0000 0000 [20x00] 0000        06EA(i=1770) 7916(30998)
        #        yaw angle (/182.05)           player_idx  data_idx       data_id
        (
            m_flags, m_type, m_palette_index,
            m_id, min_difficulty,
            pos_x, pos_y, pos_z,
            _,
            yaw,
            m3, m4, _,
            # Don't rely on
            _m_player_index, _m_data_index, _m_data_id
        ) = struct.unpack(
            """>
            L H H
            H H
            L L l
            8s
            H
            H H 20s

            H H H
            """,
            marker_data[m_start:m_end]
        )
        m_type = MarkerType(m_type)
        marker = None
        if m_palette_index < len(palette[m_type]):
            marker = palette[m_type][m_palette_index]

        pos = (pos_x / WORLD_POINT_SF, pos_y / WORLD_POINT_SF, pos_z / WORLD_POINT_SF)
        facing = yaw / ANGLE_SF

        marker_instance = {
            'marker_id': m_id,
            'type': m_type,
            'palette_index': m_palette_index,
            'tag': marker['tag'] if marker else None,
            'flags': MarkerFlag(m_flags),
            'm3': m3,
            'm4': m4,
            'min_difficulty': min_difficulty,
            'facing': facing,
            'pos': pos
        }

        if marker:
            marker['markers'][m_id] = marker_instance
        else:
            orphans['markers'][m_type][m_id] = marker_instance
            orphans['count'] = orphans['count'] + 1

        m_start = m_end

    return (palette, orphans)


def parse_map_actions(mesh_header, data):
    map_action_start = get_offset(mesh_header.map_actions_offset)
    map_action_end = map_action_start + mesh_header.map_action_buffer_size
    map_action_data = data[map_action_start:map_action_end]

    num_actions = mesh_header.map_action_count

    action_start = 0
    action_head_end = num_actions * ACTION_HEAD_SIZE
    action_data_end = 0
    ends = [0]
    actions = OrderedDict()
    for i in range(num_actions):
        action_end = action_start + ACTION_HEAD_SIZE

        (
            action_id, expiration_mode, action_type, flags, trigger_time_start, trigger_time_duration, num_params, size, offset, indent, unknown, unused
        ) = struct.unpack(
            # 887E <- action_id
            # 0000 <- expiration_mode
            # 61636C69 <- action_type
            # 0000 0001 <- flags
            # 0000 0000 <- trigger_time_start
            # 0000 0000 <- trigger_time_duration
            # 0002 <- num_params
            # 002C <- size
            # 0000 320C <- offset
            # 0000 <- indent
            # 0000 <- unknown
            # 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000
            """>
            H H
            4s
            L L L
            H
            H
            L
            H H
            32s
            """,
            map_action_data[action_start:action_end]
        )

        if all(f == b'' for f in action_type.split(b'\xff')):
            action_type = None
        else:
            action_type = myth_headers.decode_string(action_type)

        action_data_start = action_head_end + offset
        action_data_end = action_data_start + size
        action_data = map_action_data[action_data_start:action_data_end]

        param_remain = num_params
        param_start = 0
        name = ''
        parameters = []
        while param_remain:
            param_head_end = param_start + 8
            param_head_data = action_data[param_start:param_head_end]
            
            (param_type, num_values, param_name) = struct.unpack(">H H 4s", param_head_data)

            param_name = myth_headers.decode_string(param_name)

            # print(action_id, action_type, param_head_data.hex(), param_name, param_type, end=' ')

            param_type = ParamType(param_type)
            scale_factor = None
            if param_type == ParamType.STRING:
                align_num_values = align(4, num_values)
                param_bytes = align_num_values
                param_struct = f'{align_num_values}s'
            elif param_type == ParamType.WORLD_POINT_2D:
                num_values = (num_values * 2)
                param_bytes = num_values * 4
                scale_factor = WORLD_POINT_SF
                param_struct = f'{num_values}L'
            elif param_type == ParamType.FIXED:
                num_values = (num_values * 2)
                param_bytes = num_values * 2
                param_struct = f'{num_values}H'
            elif param_type == ParamType.INTEGER:
                param_bytes = num_values * 4
                param_struct = f'{num_values}L'
            elif param_type == ParamType.WORLD_DISTANCE:
                param_bytes = num_values * 4
                scale_factor = WORLD_POINT_SF
                param_struct = f'{num_values}L'
            elif param_type in [ParamType.SOUND, ParamType.FIELD_NAME]:
                param_bytes = num_values * 4
                param_struct = num_values * '4s'
            elif param_type == ParamType.FLAG:
                align_num_values = align(4, num_values)
                param_bytes = align_num_values
                param_struct = f'{align_num_values}?'
            else:
                if param_type == ParamType.ANGLE:
                    scale_factor = ANGLE_SF
                align_num_values = align(2, num_values)
                param_bytes = align_num_values * 2
                param_struct = f'{align_num_values}H'

            param_end = param_head_end + param_bytes
            param_data = action_data[param_head_end:param_end]
            param_fmt = f">{param_struct}"
            # print(param_type, param_fmt, param_data, param_bytes, len(param_data))
            param_values = struct.unpack(param_fmt, param_data)

            # Post process
            # _remainder = None
            if param_type == ParamType.STRING:
                # _remainder = param_values[0][num_values:]
                param_values = myth_headers.decode_string(param_values[0][:num_values])
            elif param_type == ParamType.FLAG:
                # Only look at the first byte
                if len(param_values):
                    param_values = param_values[0]
                else:
                    param_values = True
            else:
                # _remainder = param_values[num_values:]
                param_values = param_values[:num_values]

            if scale_factor:
                param_values = [p / scale_factor for p in param_values]

            # print(f'{param_remain:<3} \x1b[1m{param_type}\x1b[0m [{num_values}] {param_values} \x1b[1m{_remainder}\x1b[0m', param_fmt, param_data.hex())
            parameters.append({
                'type': param_type,
                'count': num_values,
                'name': param_name,
                'values': param_values
            })

            if param_name == 'name':
                name = param_values

            param_start = param_end
            param_remain = param_remain - 1

        ends.append(action_data_end)

        actions[action_id] = {
            'type': action_type,
            'action_id': action_id,
            'expiration_mode': ActionExpiration(expiration_mode),
            'name': name,
            'flags': ActionFlag(flags),
            'trigger_time_start': trigger_time_start,
            'trigger_time_duration': trigger_time_duration,
            'parameters': parameters,
            'size': size,
            'offset': offset,
            'indent': indent,
            'unknown': unknown,
            'unused': unused,
        }
        action_start = action_end
    action_remainder = map_action_data[max(ends):]
    return (actions, action_remainder)
