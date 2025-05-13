#!/usr/bin/env python3
import enum
import os

import myth_headers
import utils

DEBUG_PROJ = (os.environ.get('DEBUG_PROJ') == '1')

LPGR_SIZE = 128
LpgrFmt = ('Lpgr', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('4s', 'physics_tag'),
    ('h', 'sequence_index_flight'),
    ('h', 'sequence_index_stain'),
    ('h', 'scale_lower_bound'),
    ('h', 'scale_delta'),
    ('h', 'animation_rate_lower_bound'),
    ('h', 'animation_rate_delta'),
    ('h', 'target_number_lower_bound'),
    ('h', 'target_number_delta'),
    ('l', 'radius_lower_bound'),
    ('l', 'radius_delta'),
    ('i', 'expiration_time_lower_bound'),
    ('i', 'expiration_time_delta'),
    ('h', 'transfer_mode'),
    ('h', 'height_offset'),
    ('h', 'startup_transition_time_lower_bound'),
    ('h', 'startup_transition_time_delta'),
    ('h', 'ending_transition_time_lower_bound'),
    ('h', 'ending_transition_time_delta'),
    ('i', 'duration_lower_bound'),
    ('i', 'duration_delta'),
    ('h', 'initial_z_velocity'),
    ('h', 'z_acceleration'),
    ('h', 'startup_delay_lower_bound'),
    ('h', 'startup_delay_delta'),
    ('8x', None),
    ('4s', 'chain_to_lpgr_tag'),
    ('4s', 'local_light_tag'),
    ('28x', None),
    ('12x', None),
])

PRGR_HEAD_SIZE = 32
PrgrHeadFmt = ('PrgrHead', [
    ('L', 'flags'),
    ('h', 'number_of_parts'),
    ('2x', None),
    ('4s', 'mesh_effect'),
    ('4s', 'sound'),
    ('4s', 'local_projectile_group'),
    ('6x', None),
    ('h', 'local_projectile_group_type'),
    ('h', 'mesh_effect_type'),
    ('h', 'sound_index'),
])

PrgrProjFmt = ('PrgrProj', [
    ('4s', 'projectile_tag'),
    ('L', 'flags'),
    ('h', 'count_lower_bound'),
    ('h', 'count_delta'),
    ('h', 'position_lower_bound'),
    ('h', 'position_delta'),
    ('4x', None),
    ('h', 'appearing_faction'),
    ('2x', None),
    ('4s', 'fail_projectile_tag'),
    ('h', 'fail_projectile_type'),
    ('h', 'projectile_type'),
])

PROJ_SIZE = 320
PROJ_DMG_SIZE = 16
MAX_PROJ_SOUNDS = 4

class DamageType(enum.Enum):
    NONE = -1
    EXPLOSION = enum.auto()
    MAGICAL = enum.auto()
    HOLDING = enum.auto()
    HEALING = enum.auto()
    KINETIC = enum.auto()
    SLASHING_METAL = enum.auto()
    STONING = enum.auto()
    SLASHING_CLAWS = enum.auto()
    EXPLOSIVE_ELECTRICITY = enum.auto()
    FIRE = enum.auto()
    GAS = enum.auto()
    CHARM = enum.auto()
class DamageFlags(enum.Flag):
    PROPORTIONAL_TO_VELOCITY = enum.auto()
    AREA_OF_EFFECT = enum.auto()
    DOES_NOT_INTERRUPT_EVENTS = enum.auto()
    DAMAGE_IS_LONG_RANGE = enum.auto()
    CAN_CAUSE_PARALYSIS = enum.auto()
    CAN_STUN = enum.auto()
    CANNOT_BE_BLOCKED = enum.auto()
    CANNOT_BE_HEALED = enum.auto()
    DOES_NOT_AFFECT_MONSTERS = enum.auto()
    DETONATES_EXPLOSIVE_IMMEDIATELY = enum.auto()
    PROPORTIONAL_TO_MANA = enum.auto()
    CAN_DESTROY_LARGE_OBJECTS = enum.auto()
    INSTANTANEOUS = enum.auto()
    CANNOT_HURT_OWNER = enum.auto()
    DOES_NOT_MAKE_MONSTERS_FLINCH = enum.auto()
    CAN_CAUSE_CONFUSION = enum.auto()
ProjDmgFmt = ('ProjDmg', [
    ('h', 'type', DamageType),
    ('H', 'flags', DamageFlags),
    ('h', 'damage_lower_bound', 256),
    ('h', 'damage_delta', 256),
    ('h', 'radius_lower_bound', 512),
    ('h', 'radius_delta', 512),
    ('h', 'rate_of_expansion', 512),
    ('h', 'damage_to_velocity', 256),
])

class ProjFlags(enum.Flag):
    USES_OWNER_COLOR_TABLE_INDEX = enum.auto()
    IS_GUIDED = enum.auto()
    IS_BLOODY = enum.auto()
    DETONATES_WHEN_ANIMATION_LOOPS = enum.auto()
    DETONATES_WHEN_TRANSFER_LOOPS = enum.auto()
    DETONATES_AT_REST = enum.auto()
    AFFECTED_BY_WIND = enum.auto()
    ANIMATES_AT_REST = enum.auto()
    BECOMES_DORMANT_AT_REST = enum.auto()
    CAN_ANIMATE_BACKWARDS = enum.auto()
    CONTRAIL_FREQUENCY_RESETS_AFTER_BOUNCING = enum.auto()
    CAN_BE_MIRRORED = enum.auto()
    PROMOTED_AT_END_OF_LIFESPAN = enum.auto()
    MELEE_ATTACK = enum.auto()
    CANNOT_BE_ACCELERATED = enum.auto()
    BLOODIES_LANDSCAPE = enum.auto()
    IS_ON_FIRE = enum.auto()
    REMAINS_AFTER_DETONATION = enum.auto()
    PASSES_THROUGH_TARGET = enum.auto()
    CANNOT_BE_MIRRORED_VERTICALLY = enum.auto()
    FLOATS = enum.auto()
    IS_MEDIA_SURFACE_EFFECT = enum.auto()
    DAMAGE_PROPORTIONAL_TO_MANA = enum.auto()
    IS_ONLY_DESTROYED_BY_LIFESPAN = enum.auto()
    IS_LIGHTNING = enum.auto()
    CHOOSES_NEARBY_TARGET = enum.auto()
    CONTINUALLY_DETONATES = enum.auto()
    MAKES_OWNER_MONSTER_VISIBLE = enum.auto()
    CAN_SET_LANDSCAPE_ON_FIRE = enum.auto()
    CENTERED_ON_TARGET = enum.auto()
    MARKS_TARGET_AS_HAVING_BEEN_CHOSEN = enum.auto()
    DETONATES_IMMEDIATELY = enum.auto()

ProjFmt = ('Proj', [
    ('L', 'flags', ProjFlags),
    ('4s', 'collection_tag'),
    ('h', 'flight_sequence'),
    ('h', 'debris_sequence'),
    ('h', 'bounce_sequence'),
    ('h', 'splash_or_rebound_effect_type'),
    ('4s', 'detonation_projectile_group_tag'),
    ('4s', 'contrail_projectile_tag'),
    ('h', 'ticks_between_contrails'),
    ('h', 'maximum_contrail_count'),
    ('4s', 'object_tag'),
    ('h', 'inertia_lower_bound'),
    ('h', 'inertia_delta'),
    ('h', 'random_initial_velocity'),
    ('h', 'volume'),
    ('H', 'tracking_priority'),
    ('H', 'promotion_on_detonation_fraction'),
    ('H', 'detonation_frequency'),
    ('H', 'media_detonation_frequency'),
    ('H', 'detonation_velocity'),
    ('H', 'projectile_class'),
    ('4s', 'lightning_tag'),
    ('4x', None),
    ('4s', 'flight_sound_tag'),
    ('4s', 'rebound_sound_tag'),
    ('4s', 'sound_tag_3'),
    ('4s', 'sound_tag_4'),
    ('h', 'animation_rate_lower_bound'),
    ('h', 'animation_rate_delta'),
    ('h', 'lifespan_lower_bound'),
    ('h', 'lifespan_delta'),
    ('H', 'initial_contrail_frequency'),
    ('H', 'final_contrail_frequency'),
    ('H', 'contrail_frequency_delta'),
    ('H', 'guided_turning_speed'),
    ('4s', 'promoted_projectile_tag'),
    ('4s', 'promotion_projectile_group_tag'),
    ('H', 'maximum_safe_acceleration'),
    ('H', 'acceleration_detonation_fraction'),
    ('16s', 'damage', utils.codec(ProjDmgFmt)),
    ('4s', 'artifact_tag'),
    ('4s', 'target_detonation_projectile_group_tag'),
    ('4s', 'geometry_tag'),
    ('h', 'delay_lower_bound'),
    ('h', 'delay_delta'),
    ('4s', 'local_projectile_group_tag'),
    ('h', 'nearby_target_radius'),
    ('h', 'exclude_nearby_target_radius'),
    ('4s', 'promotion_unit_tag'),
    ('4s', 'script_tag'),
    ('71x', None),
    ('c', 'use_accel'),
    ('32x', None),
])

LIGHTNING_SIZE = 128
LightningFmt = ('Lightning', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('l', 'shock_duration'),
    ('l', 'fade_duration'),
    ('l', 'bolt_length'),
    ('h', 'sequence_fork'),
    ('h', 'sequence_bolt'),
    ('h', 'sequence_stain'),
    ('h', 'velocity'),
    ('h', 'scale'),
    ('h', 'fork_segment_minimum'),
    ('h', 'fork_segment_delta'),
    ('h', 'fork_overlap_amount'),
    ('h', 'main_bolt_overlap_amount'),
    ('H', 'angular_limit'),
    ('16s', 'damage', utils.codec(ProjDmgFmt)),
    ('h', 'apparent_number_of_bolts'),
    ('h', 'collection_reference_index'),
    ('h', 'collection_index'),
    ('h', 'color_table_index'),
])

def parse_lpgr(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + LPGR_SIZE
    return utils.codec(LpgrFmt)(data[start:end])

def parse_prgr(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + PRGR_HEAD_SIZE
    prgr_head = utils.codec(PrgrHeadFmt)(data[start:end])
    proj_start = end

    proj_list_codec = utils.list_codec('PrgrProjList', prgr_head.number_of_parts, PrgrProjFmt)
    proj_list = proj_list_codec(data[proj_start:])

    return (prgr_head, proj_list)

def parse_proj(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + PROJ_SIZE
    return utils.codec(ProjFmt)(data[start:end])

def parse_lightning(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + LIGHTNING_SIZE
    return utils.codec(LightningFmt)(data[start:end])
