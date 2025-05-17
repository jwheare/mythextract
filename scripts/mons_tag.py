#!/usr/bin/env python3
import enum
import os
import struct

import myth_headers
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
class AttackFlag(enum.Flag):
    IS_INDIRECT = enum.auto()
    DOES_NOT_REQUIRE_A_FIRING_SOLUTION = enum.auto()
    AIMED_AT_TARGETS_FEET = enum.auto()
    LEADS_TARGET = enum.auto()
    USES_AMMUNITION = enum.auto()
    USES_CARRIED_PROJECTLE = enum.auto()
    IS_REFLEXIVE = enum.auto()
    IS_SPECIAL_ABILITY = enum.auto()
    CANNOT_BE_ABORTED = enum.auto()
    IS_PRIMARY_ATTACK = enum.auto()
    AVOIDS_FRIENDLY_UNITS = enum.auto()
    VS_GIANT_SIZED = enum.auto()
    PROHIBITED_VS_GIANT_SIZED = enum.auto()
    IS_FIXED_PITCH = enum.auto()
    DONT_SHOOT_OVER_NEARBY_UNITS = enum.auto()
    LOB_TO_HIT_LOWER_NEARBY_UNITS = enum.auto()

MAX_ATTACKS = 4
MAX_ATTACK_SEQS = 4
AttackSequenceFmt = ('AttackSequence', [
    ('H', 'flags'),
    ('h', 'sequence_index'),
    ('H', 'skip_fraction'),
    ('2x', None),
])

AttackDefFmt = ('AttackDef', [
    ('H', 'flags', AttackFlag),
    ('H', 'miss_fraction', (1 << 16)),
    ('4s', 'projectile_tag'),
    ('h', 'minimum_range', 512),
    ('h', 'maximum_range', 512),
    ('32s', 'sequences', utils.list_codec(
       'AttackSequences', MAX_ATTACK_SEQS, AttackSequenceFmt,
       filter_fun=lambda _self, seq: seq.sequence_index > -1,
       empty_value=utils.encode_data(AttackSequenceFmt, (1, -1, 0)),
    )),
    ('h', 'repetitions'),
    ('h', 'initial_velocity_lower_bound', 512),
    ('h', 'initial_velocity_delta', 512),
    ('h', 'initial_velocity_error', 512),
    ('h', 'recovery_time', 30),
    ('h', 'recovery_time_experience_delta', 30),
    ('h', 'velocity_improvement_with_experience', 512),
    ('h', 'mana_cost', 255),
    ('H', 'extra_flags'),
    ('2x', None),
])

class MonsFlag(enum.Flag):
    TRANSLATES_CONTINUOUSLY = enum.auto()
    HOLDS_WITH_CLEAR_SHOT = enum.auto()
    FLOATS = enum.auto()
    FLIES = enum.auto()
    ALLOWS_PROJECTILES_TO_PASS_THROUGH = enum.auto()
    EXPERIENCE_PROPORTIONAL_TO_DAMAGE = enum.auto()
    IS_ANTI_MISSILE_UNIT = enum.auto()
    IS_ANTI_MISSILE_TARGET = enum.auto()
    TURNS_TO_STONE_WHEN_KILLED = enum.auto()
    CONCENTRATES_ON_SINGLE_TARGET = enum.auto()
    IS_UNDEAD = enum.auto()
    CANNOT_BE_AUTOTARGETED = enum.auto()
    IS_GIANT_SIZED = enum.auto()
    DOES_NOT_RESPECT_VISIBILITY = enum.auto()
    IS_NOT_SOLID = enum.auto()
    LEAVES_CONTRAIL = enum.auto()
    INVISIBLE_ON_OVERHEAD_MAP = enum.auto()
    CANNOT_BE_HEALED_BY_DAMAGE = enum.auto()
    DOES_NOT_DROP_AMMO_WHEN_DYING = enum.auto()
    IS_INANIMATE_OBJECT = enum.auto()
    USE_EXTENDED = enum.auto()
    ALLOW_MULTIPLE_ARTIFACTS = enum.auto()
    HAS_BURNING_DEATH = enum.auto()
    CAN_BE_PROPELLED = enum.auto()
    RAISE_TO_FLYING_HEIGHT = enum.auto()
    IF_AMBIENT_CAN_BE_TARGETED_NORMALLY = enum.auto()
    MORALE_CAN_BE_BOOSTED = enum.auto()
    AFFECTS_MORALE = enum.auto()
    ALWAYS_USES_ENTRANCE_PROJECTILE_GROU = enum.auto()
    CAN_EXTEND_CHARGE_DURRATION = enum.auto()
    IGNORES_TERRAIN_COSTS_FOR_IMPASSABILITY = enum.auto()
    LIMITED_CHARGE_DURRATION = enum.auto()

class MonsClass(enum.Enum):
    MELEE = 0
    MISSILE = enum.auto()
    SUICIDE = enum.auto()
    SPECIAL = enum.auto()
    HARMLESS = enum.auto()
    AMBIENT_LIFE = enum.auto()
    INVISIBLE_OBSERVER = enum.auto()

MonsMovementModsFmt = ('MonsMovementMods', [
    ('B', 'dwarf_depth_media', 255),
    ('B', 'human_depth_media', 255),
    ('B', 'giant_depth_media', 255),
    ('B', 'deep', 255),
    ('B', 'sloped', 255),
    ('B', 'steep', 255),
    ('B', 'grass', 255),
    ('B', 'desert', 255),
    ('B', 'rocky', 255),
    ('B', 'marsh', 255),
    ('B', 'snow', 255),
    ('B', 'unused_0', 255),
    ('B', 'unused_1', 255),
    ('B', 'unused_2', 255),
    ('B', 'walking_impassable', 255),
    ('B', 'flying_impassable', 255),
])

class ExtendedFlagsSloped(enum.Flag, boundary=enum.CONFORM):
    MOVES_TO_POSITION_TO_SHOOT_UPHILL = enum.auto()
    SHIFT_CLICK_TARGETS_GROUP = enum.auto()
    WALKS_AROUND_LARGE_UNIT_BLOCKAGES = enum.auto()
    CHASES_ENEMIES_INTELLIGENTLY = enum.auto()
    RESPONDS_TO_ENEMIES_WHEN_ATTACKING = enum.auto()
    CAN_TARGET_FLYING_UNITS = 7

class ExtendedFlagsGrass(enum.Flag, boundary=enum.CONFORM):
    DOESNT_CLOSE_ON_TARGET = enum.auto()
    RESIZABLE_SELECTION_BOX = enum.auto()
    UNIT_CAN_CHARGE = enum.auto()
    TURNS_IN_A_CURVE = enum.auto()
    ENEMIES_CANT_SEE_MANA = enum.auto()
    MANA_ISNT_SHOWN = enum.auto()
    MIXES_MISSILE_MELEE_BEHAVIOUR = enum.auto()
    HAS_LONG_RANGE_EYESIGHT = enum.auto()

class ExtendedFlagsDesert(enum.Flag, boundary=enum.CONFORM):
    DOUBLE_CLICK_SELECTS_MONSTER_TYPE = enum.auto()
    MISSILE_ATTACK_NOT_HEIGHT_AFFECTED = enum.auto()
    DOESNT_FLINCH_WHEN_HEALED = enum.auto()
    CHASES_ENEMY_DURING_ATTACK_RECOVERY = enum.auto()
    WALKS_ON_THE_SURFACE_OF_WATER = enum.auto()
    DOESNT_AUTOTARGET_ENEMIES = enum.auto()
    EXTRA_AGGRESSIVE_MISSILE_UNIT = enum.auto()
    ADJUST_BLOCK_RATE = enum.auto()

MonsTerrainCostsFmt = ('MonsTerrainCosts', [
    ('b', 'dwarf_depth_media'), # unused in extended flags?
    ('b', 'human_depth_media'), # unused in extended flags?
    ('b', 'giant_depth_media'), # unused in extended flags?
    ('b', 'deep'), # unused in extended flags?
    ('b', 'sloped'), # ExtendedFlagsSloped
    ('b', 'steep'), # block_delay_rate - Block delay modifier (between -29 and 127)
    ('b', 'grass'), # ExtendedFlagsGrass
    ('b', 'desert'), # ExtendedFlagsDesert
    ('b', 'rocky'), # run_speed - Speed modifier
    ('b', 'marsh'), # maximum_experience_points - Max. Experience
    ('b', 'snow'), # charge_range - Charge Range (WU)
    ('b', 'unused_0'), # unused in extended flags?
    ('b', 'unused_1'),  # unused in extended flags?
    ('b', 'unused_2'),  # unused in extended flags?
    ('b', 'walking_impassable'),  # unused in extended flags?
    ('b', 'flying_impassable'),  # unused in extended flags?
])

def extended_flags(mons_tag):
    return {
        'flags1': ExtendedFlagsSloped(mons_tag.terrain_costs.sloped),
        'block_delay_rate': mons_tag.terrain_costs.steep,
        'flags2': ExtendedFlagsGrass(mons_tag.terrain_costs.grass),
        'flags3': ExtendedFlagsDesert(mons_tag.terrain_costs.desert),
        'run_speed': mons_tag.terrain_costs.rocky,
        'maximum_experience_points': mons_tag.terrain_costs.marsh,
        'charge_range': mons_tag.terrain_costs.snow,
    }

def terrain_passability(mons_tag):
    # Based on Myth code
    gameplay_lte_170 = False
    gameplay_gt_130 = True

    # This flag is not on by default, and likely has never been turned on
    ignore_costs = MonsFlag.IGNORES_TERRAIN_COSTS_FOR_IMPASSABILITY in mons_tag.flags
    # Given the above, this will likely be true, even though we're above 1.7.0
    use_terrain_costs = gameplay_lte_170 or not ignore_costs
    # This will also be true, we're above 1.3.0
    use_movement_modifiers = gameplay_gt_130

    passability = {}
    for terrain_type, terrain_cost in mons_tag.terrain_costs._asdict().items():
        movement_modifier = getattr(mons_tag.movement_modifiers, terrain_type)

        if (
            (use_terrain_costs and terrain_cost < 0) or
            (use_movement_modifiers and movement_modifier == 0)
        ):
            passability[terrain_type] = False
        else:
            passability[terrain_type] = True
    return passability

class Size(enum.Enum):
    SMALL = 0
    MAN = enum.auto()
    GIANT = enum.auto()

class SoundTypes(enum.Enum):
    NONE = -1
    ATTACK_ORDER = enum.auto()
    MULTIPLE_ATTACK_ORDER = enum.auto()
    ATTACK_ORDER_VS_UNDEAD = enum.auto()
    MOVE_ORDER = enum.auto()
    MULTIPLE_MOVE_ORDER = enum.auto()
    SELECTION = enum.auto()
    MULTIPLE_SELECTION = enum.auto()
    HIT_FRIENDLY_UNIT = enum.auto()
    HIT_BY_FRIENDLY_UNIT = enum.auto()
    ATTACK_OBSTRUCTED_BY_FRIENDLY_UNIT = enum.auto()
    ATTACK_ENEMY_UNIT = enum.auto()
    ATTACK_ENEMY_WITH_FRIENDLY_UNITS_NEARBY = enum.auto()
    SPRAYED_BY_GORE = enum.auto()
    CAUSED_ENEMY_DEATH = enum.auto()
    CAUSED_FRIENDLY_DEATH = enum.auto()
    CAUSED_DEATH_OF_ENEMY_UNDEAD = enum.auto()
    # CAUSED_MULTIPLE_ENEMY_DEATHS = 16 # commented in oak

MonsTagFmt = ('MonsTag', [
    ('L', 'flags', MonsFlag),
    ('4s', 'collection_tag'),
    ('52s', 'sequence_indexes', utils.list_pack('MonsSeqIndexes', 26, '>h')),
    ('4s', 'burning_death_projectile_group_tag'),
    ('h', 'burning_death_projectile_group_type'),
    ('B', 'experience_kill_bonus'),
    ('B', 'experience_bonus_radius'),
    ('H', 'propelled_system_shock'),
    ('H', 'damage_to_propulsion'),
    ('16s', 'terrain_costs', utils.codec(MonsTerrainCostsFmt)),
    ('H', 'terrain_impassability_flags'), # set at runtime
    ('h', 'pathfinding_radius'),
    ('16s', 'movement_modifiers', utils.codec(MonsMovementModsFmt)),
    ('H', 'absorbed_fraction', 1 << 16),
    ('h', 'warning_distance'),
    ('h', 'critical_distance'),
    ('h', 'healing_fraction', 255),
    ('h', 'initial_ammunition_lower_bound'),
    ('h', 'initial_ammunition_delta'),
    ('h', 'activation_distance'),
    ('2x', None),

    ('H', 'turning_speed', (0xffff / 360) / 30),
    ('h', 'base_movement_speed'),
    ('H', 'left_handed_fraction'),
    ('h', 'size', Size),
    ('4s', 'object_tag'),
    ('h', 'number_of_attacks'),
    ('h', 'desired_projectile_volume'),
    ('256s', 'attacks', utils.list_codec(
        'Attacks', MAX_ATTACKS, AttackDefFmt,
        filter_fun=lambda self, attack: not utils.all_off(attack.projectile_tag)
    )),
    ('4s', 'map_action_tag'),
    ('h', 'attack_frequency_lower_bound'),
    ('h', 'attack_frequency_delta'),
    ('4s', 'exploding_projectile_group_tag'),
    ('h', 'hack_flags'),
    ('h', 'maximum_ammunition_count'),
    ('H', 'hard_death_system_shock'),
    ('H', 'flinch_system_shock', 1 << 16),
    ('4s', 'melee_impact_projectile_group_tag'),
    ('4s', 'dying_projectile_group_tag'),
    ('4s', 'spelling_string_list_tag'),
    ('4s', 'names_string_list_tag'),
    ('4s', 'flavor_string_list_tag'),
    ('b', 'use_attack_frequency'),
    ('b', 'more_hack_flags'),
    ('h', 'monster_class', MonsClass),
    ('h', 'monster_allegiance'),
    ('h', 'experience_point_value'),
    ('40s', 'sound_tags', utils.list_pack(
        'MonsSoundTags', 10, '>4s',
        filter_fun=lambda self, tag: not utils.all_on(tag),
        empty_value=struct.pack('>l', -1)
    )),
    ('4s', 'blocked_impact_projectile_group_tag'),
    ('4s', 'absorbed_impact_projectile_group_tag'),
    ('4s', 'ammunition_projectile_tag'),
    ('h', 'visibility_type'),
    ('h', 'combined_power'),
    ('h', 'longest_range', 512),
    ('h', 'cost'),
    ('10s', 'sound_types', utils.list_pack('MonsSoundTypes', 10, '>b')),
    ('h', 'enemy_experience_kill_bonus'),
    ('4s', 'entrance_projectile_group_tag'),
    ('4s', 'local_projectile_group_tag'),
    ('4s', 'special_ability_string_list_tag'),
    ('4s', 'exit_projectile_group_tag'),
    ('h', 'maximum_mana', 256),
    ('h', 'mana_recharge_rate', 256),
    ('H', 'berserk_system_shock', 1 << 16),
    ('H', 'berserk_vitality', 1 << 16),
    ('h', 'maximum_artifacts_carried'),
    ('2x', None),
    ('4s', 'initial_artifacts_projectile_group_tag'),
    ('L', 'extra_flags'),
    ('208x', None),
    ('264x', None),
])

class ObjeFlags(enum.Flag):
    DRAW_SELECTION_BOX = enum.auto()
    DRAW_VITALITY_BOX = enum.auto()
    MAINTAINS_CONSTANT_HEIGHT_ABOVE_MESH = enum.auto()
    IGNORE_MODEL_AND_OBJECT_COLLISIONS = enum.auto()
    OBJECT_IS_SOLID = enum.auto()
    OBJECT_CANNOT_BE_DEFLECTED = enum.auto()
    OBJECT_IGNORES_AREA_OF_EFFECT_DAMAGE = enum.auto()
    OBJECT_NOT_ACCELERATED_BY_DAMAGE = enum.auto()

ObjeEffectFmt = ('ObjeEffect', [
    ('h', 'slashing_damage', 256),
    ('h', 'kinetic_damage', 256),
    ('h', 'explosive_damage', 256),
    ('h', 'electric_damage', 256),
    ('h', 'fire_damage', 256),
    ('h', 'paralysis_duration', 256),
    ('h', 'stone', 256),
    ('h', 'gas_damage', 256),
    ('h', 'confusion', 256),
    ('14x', None),
])

UnitTagFmt = ('UnitTag', [
    ('4s', 'mons'),
    ('4s', 'core'),
])

ObjeTagFmt = ('ObjeTag', [
    ('h', 'flags', ObjeFlags),
    ('h', 'gravity', 512),
    ('h', 'elasticity', 255),
    ('h', 'terminal_velocity', 512),
    ('h', 'vitality_lower_bound', 255),
    ('h', 'vitality_delta', 255),
    ('h', 'scale_lower_bound', 255),
    ('h', 'scale_delta', 255),
    ('32s', 'effect_modifiers', utils.codec(ObjeEffectFmt)),
    ('h', 'minimum_damage', 255),
    ('14x', None),
])

SequenceNames = [
    "idle_1",
    "moving",
    "placeholder",
    "pause",
    "turning",
    "blocking",
    "damage",
    "pickup",
    "head_shots",
    "celebration",
    "trans_1-2",
    "idle_2",
    "trans_2-1",
    "running",
    "ammo",
    "holding",
    "taunting",
    "gliding",
    "propelled",
]

ARTIFACT_SIZE = 168
MAX_ARTI_PROJ = 4
MAX_ARTI_EFFECT_MODS = 16
ArtifactFmt = ('Artifact', [
    ('L', 'flags'),
    ('4s', 'monster_restriction_tag'),
    ('h', 'specialization_restriction'),
    ('h', 'initial_charges_lower_bound'),
    ('h', 'initial_charges_delta'),
    ('h', 'pad'),
    ('4s', 'collection_tag'),
    ('h', 'sequence_inventory'),
    ('h', 'sequence_2'),
    ('h', 'sequence_3'),
    ('h', 'sequence_4'),
    ('16s', 'projectile_tags', utils.list_pack('ArtifactProjTags', MAX_ARTI_PROJ, '>4s')),
    ('L', 'bonus_monster_flags'),
    ('h', 'monster_override_type'),
    ('h', 'expiry_timer'),
    ('32s', 'bonus_effect_modifiers', utils.list_pack('ArtifactEffectMods', MAX_ARTI_EFFECT_MODS, '>h')),
    ('64s', 'override_attack', utils.codec(AttackDefFmt)),
    ('4s', 'special_ability_string_list_tag'),
    ('4s', 'monster_override_tag'),
    ('h', 'collection_index'),
    ('h', 'special_ability_string_list_index'),
    ('8s', 'projectile_types', utils.list_pack('ArtifactProjTypes', MAX_ARTI_PROJ, '>h')),
])

def sequence_name(idx):
    if idx < len(SequenceNames):
        return SequenceNames[idx]
    else:
        return ''

def parse_artifact(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + ARTIFACT_SIZE
    return utils.codec(ArtifactFmt)(data[start:end])

def parse_unit(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + 8
    return utils.codec(UnitTagFmt)(data[myth_headers.TAG_HEADER_SIZE:end])

def parse_obje(data):
    return utils.codec(ObjeTagFmt, offset=myth_headers.TAG_HEADER_SIZE)(data)

def parse_tag(data):
    return utils.codec(MonsTagFmt, offset=myth_headers.TAG_HEADER_SIZE)(data)

def encode_tag(tag_header, mons_tag):
    tag_data = mons_tag.value

    tag_data_size = len(tag_data)

    # Adjust tag header size
    new_tag_header = tag_header._replace(
        destination=-1,
        identifier=-1,
        type=0,
        tag_data_size=tag_data_size
    )
    return (
        myth_headers.encode_header(new_tag_header)
        + tag_data
    )
