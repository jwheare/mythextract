#!/usr/bin/env python3
from collections import namedtuple
import os
import struct

import myth_headers

DEBUG_PROJ = (os.environ.get('DEBUG_PROJ') == '1')

LPGR_SIZE = 128
MAX_LPGR_SEQ = 2
LpgrFmt = """>
    L
    4s 4s
    h h
    h h
    h h h
    h l l
    i i h
    h h h
    h h i
    i h h
    h h
    8x
    4s 4s
    28x
    12x
"""
Lpgr = namedtuple('Lpgr', [
    'flags',
    'collection_reference_tag',
    'physics_tag',
    'sequence_index_flight',
    'sequence_index_stain',
    'scale_lower_bound',
    'scale_delta',
    'animation_rate_lower_bound',
    'animation_rate_delta',
    'target_number_lower_bound',
    'target_number_delta',
    'radius_lower_bound',
    'radius_delta',
    'expiration_time_lower_bound',
    'expiration_time_delta',
    'transfer_mode',
    'height_offset',
    'startup_transition_time_lower_bound',
    'startup_transition_time_delta',
    'ending_transition_time_lower_bound',
    'ending_transition_time_delta',
    'duration_lower_bound',
    'duration_delta',
    'initial_z_velocity',
    'z_acceleration',
    'startup_delay_lower_bound',
    'startup_delay_delta',
    'chain_to_lpgr_tag',
    'local_light_tag',
])

PRGR_HEAD_SIZE = 32
PrgrHeadFmt = """>
    L
    h
    2x
    4s
    4s
    4s
    6x
    h
    h
    h
"""
PRGR_PROJ_SIZE = 32
PrgrProjFmt = """>
    4s
    L
    h
    h
    h
    h
    4x
    h
    2x
    4s
    h
    h
"""
PrgrHead = namedtuple('PrgrHead', [
    'flags',
    'number_of_parts',
    'mesh_effect',
    'sound',
    'local_projectile_group',
    'local_projectile_group_type',
    'mesh_effect_type',
    'sound_index',
])
PrgrProj = namedtuple('PrgrProj', [
    'projectile_tag',
    'flags',
    'count_lower_bound',
    'count_delta',
    'position_lower_bound',
    'position_delta',
    'appearing_faction',
    'fail_projectile_tag',
    'fail_projectile_type',
    'projectile_type',
])

PROJ_SIZE = 320
PROJ_DMG_SIZE = 16
MAX_PROJ_SOUNDS = 4
ProjDmgFmt = """>
    H
    H
    h
    h
    h
    h
    h
    h
"""
ProjDmg = namedtuple('ProjDmg', [
    'type',
    'flags',
    'damage_lower_bound',
    'damage_delta',
    'radius_lower_bound',
    'radius_delta',
    'rate_of_expansion',
    'damage_to_velocity',
])
ProjFmt = """>
    L
    4s
    h
    h
    h
    h
    4s
    4s
    h
    h
    4s
    h
    h
    h
    h
    H
    H
    H
    H
    H
    H
    4s
    4x
    4s
    4s
    4s
    4s
    h
    h
    h
    h
    H
    H
    H
    H
    4s
    4s
    H
    H
    16s
    4s
    4s
    4s
    h
    h
    4s
    h
    h
    4s
    4s
    71x
    c
    32x
"""
Proj = namedtuple('Proj', [
    'flags',
    'collection_tag',
    'flight_sequence',
    'debris_sequence',
    'bounce_sequence',
    'splash_or_rebound_effect_type',
    'detonation_projectile_group_tag',
    'contrail_projectile_tag',
    'ticks_between_contrails',
    'maximum_contrail_count',
    'object_tag',
    'inertia_lower_bound',
    'inertia_delta',
    'random_initial_velocity',
    'volume',
    'tracking_priority',
    'promotion_on_detonation_fraction',
    'detonation_frequency',
    'media_detonation_frequency',
    'detonation_velocity',
    'projectile_class',
    'lightning_tag',
    'flight_sound_tag',
    'rebound_sound_tag',
    'sound_tag_3',
    'sound_tag_4',
    'animation_rate_lower_bound',
    'animation_rate_delta',
    'lifespan_lower_bound',
    'lifespan_delta',
    'initial_contrail_frequency',
    'final_contrail_frequency',
    'contrail_frequency_delta',
    'guided_turning_speed',
    'promoted_projectile_tag',
    'promotion_projectile_group_tag',
    'maximum_safe_acceleration',
    'acceleration_detonation_fraction',
    'damage',
    'artifact_tag',
    'target_detonation_projectile_group_tag',
    'geometry_tag',
    'delay_lower_bound',
    'delay_delta',
    'local_projectile_group_tag',
    'nearby_target_radius',
    'exclude_nearby_target_radius',
    'promotion_unit_tag',
    'script_tag',
    'use_accel',
])

LIGHTNING_SIZE = 128
LightningFmt = """>
    L
    4s
    l
    l
    l
    h
    h
    h
    h
    h
    h
    h
    h
    h
    H
    16s
    h
    h
    h
    h
"""
Lightning = namedtuple('Lightning', [
    'flags',
    'collection_reference_tag',
    'shock_duration',
    'fade_duration',
    'bolt_length',
    'sequence_fork',
    'sequence_bolt',
    'sequence_stain',
    'velocity',
    'scale',
    'fork_segment_minimum',
    'fork_segment_delta',
    'fork_overlap_amount',
    'main_bolt_overlap_amount',
    'angular_limit',
    'damage',
    'apparent_number_of_bolts',
    'collection_reference_index',
    'collection_index',
    'color_table_index',
])

def parse_lpgr(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + LPGR_SIZE
    return Lpgr._make(struct.unpack(LpgrFmt, data[start:end]))

def parse_prgr(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + PRGR_HEAD_SIZE
    prgr_head = PrgrHead._make(struct.unpack(PrgrHeadFmt, data[start:end]))

    proj_list = []
    proj_start = end
    for i in range(prgr_head.number_of_parts):
        proj_end = proj_start + PRGR_PROJ_SIZE
        proj = PrgrProj._make(struct.unpack(PrgrProjFmt, data[proj_start:proj_end]))
        proj_list.append(proj)
        proj_start = proj_end

    return (prgr_head, proj_list)

def parse_proj(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + PROJ_SIZE
    proj = Proj._make(struct.unpack(ProjFmt, data[start:end]))
    return proj._replace(damage=ProjDmg._make(struct.unpack(ProjDmgFmt, proj.damage)))

def parse_lightning(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + LIGHTNING_SIZE
    lightning = Lightning._make(struct.unpack(LightningFmt, data[start:end]))
    return lightning._replace(damage=ProjDmg._make(struct.unpack(ProjDmgFmt, lightning.damage)))
