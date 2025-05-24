#!/usr/bin/env python3
import enum
import os
import struct

import myth_headers
import codec

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
    ('H', 'miss_fraction', codec.Fixed),
    ('4s', 'projectile_tag'),
    ('h', 'minimum_range', codec.World),
    ('h', 'maximum_range', codec.World),
    ('32s', 'sequences', codec.list_codec(
       MAX_ATTACK_SEQS, AttackSequenceFmt,
       filter_fun=lambda _self, seq: seq.sequence_index > -1,
       empty_value=codec.encode_data(AttackSequenceFmt, (1, -1, 0)),
    )),
    ('h', 'repetitions'),
    ('h', 'initial_velocity_lower_bound', codec.World),
    ('h', 'initial_velocity_delta', codec.world_delta('initial_velocity_lower_bound')),
    ('h', 'initial_velocity_error', codec.World),
    ('h', 'recovery_time', codec.Time),
    ('h', 'recovery_time_experience_delta', codec.Time),
    ('h', 'velocity_improvement_with_experience', codec.World),
    ('h', 'mana_cost', codec.ShortFixed),
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

class MonsExtraFlag(enum.Flag):
    HIDE_OWNER_NAME = enum.auto()
    DONT_AUTOEQUIP_INITIAL_ARTIFACTS = enum.auto()

class MonsClass(enum.Enum):
    MELEE = 0
    MISSILE = enum.auto()
    SUICIDE = enum.auto()
    SPECIAL = enum.auto()
    HARMLESS = enum.auto()
    AMBIENT_LIFE = enum.auto()
    INVISIBLE_OBSERVER = enum.auto()

MonsMovementModsFmt = ('MonsMovementMods', [
    ('B', 'dwarf_depth_media', codec.ShortPercent),
    ('B', 'human_depth_media', codec.ShortPercent),
    ('B', 'giant_depth_media', codec.ShortPercent),
    ('B', 'deep', codec.ShortPercent),
    ('B', 'sloped', codec.ShortPercent),
    ('B', 'steep', codec.ShortPercent),
    ('B', 'grass', codec.ShortPercent),
    ('B', 'desert', codec.ShortPercent),
    ('B', 'rocky', codec.ShortPercent),
    ('B', 'marsh', codec.ShortPercent),
    ('B', 'snow', codec.ShortPercent),
    ('B', 'unused_0', codec.ShortPercent),
    ('B', 'unused_1', codec.ShortPercent),
    ('B', 'unused_2', codec.ShortPercent),
    ('B', 'walking_impassable', codec.ShortPercent),
    ('B', 'flying_impassable', codec.ShortPercent),
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
    ('b', 'steep'), # block_timer_cost - Block delay modifier (between -29 and 127)
    ('b', 'grass'), # ExtendedFlagsGrass
    ('b', 'desert'), # ExtendedFlagsDesert
    ('b', 'rocky'), # run_speed_modifier - Speed modifier
    ('b', 'marsh'), # maximum_experience_points - Max. Experience
    ('b', 'snow'), # charge_range - Charge Range (WU)
    ('b', 'unused_0'), # unused in extended flags?
    ('b', 'unused_1'),  # unused in extended flags?
    ('b', 'unused_2'),  # unused in extended flags?
    ('b', 'walking_impassable'),  # unused in extended flags?
    ('b', 'flying_impassable'),  # unused in extended flags?
])

def extended_flags(mons_tag):
    rocky_unsigned = codec.unsigned8(mons_tag.terrain_costs.rocky)
    marsh_unsigned = codec.unsigned8(mons_tag.terrain_costs.marsh)
    return {
        'flags1': ExtendedFlagsSloped(mons_tag.terrain_costs.sloped),
        # Default block_timer_cost is 30 ticks, this lets you modify it
        # We need to reinterpret this as a signed int
        # down to 1 ticks (30-29)
        # up to 157 ticks (30+127)
        # Range of a signed byte is -128 to 127 so we clamp at -29
        # We add the default 30 ticks, then divide by 30 for a value in seconds
        # example:  60 -> ( 60+30)/30 = 3.000
        # example: -29 -> (-29+30)/30 = 0.033
        # example: 127 -> (127+30)/30 = 5.233
        'block_timer_cost': (max(-29, mons_tag.terrain_costs.steep) + 30) / 30,
        'flags2': ExtendedFlagsGrass(mons_tag.terrain_costs.grass),
        'flags3': ExtendedFlagsDesert(mons_tag.terrain_costs.desert),
        # For running units, by default their distance travelled per tick is doubled (100% increase)
        # This value lets you modify the distance (therefore speed)
        # The value is a percentage from 1-255         (distance += distance * (value / 100))
        # If the value is 0 the modifier is set to 20% (distance += distance / 5)
        # example:     0 -> 1.200 ( 20%)
        # example:     1 -> 1.010 (  1%)
        # example:    10 -> 1.100 ( 10%)
        # example:    20 -> 1.200 ( 20%)
        # example:    50 -> 1.500 ( 50%)
        # example:   100 -> 2.000 (100%)
        # example:   127 -> 2.270 (127%)
        # example:   255 -> 3.550 (255%)
        'run_speed_modifier': 1 + (rocky_unsigned / 100.0 if rocky_unsigned > 0 else 0.2),
        # Default max experience benefit is from 5 kills
        # This value lets you change that, unsigned up to 255, 0 = default (5)
        'maximum_experience_points': marsh_unsigned if marsh_unsigned != 0 else 5,
        # Values below 1 have no further effect
        'charge_range': min(1, mons_tag.terrain_costs.snow),
    }

# int val = terrain_costs[_terrain_steep];
# if (val < -29) val = -29;
# val += 30;

# SetEditTextAsFloat(theDialog, iBlockChance, (float)val / 30.0f, 3);

# // Blocking values are only valid between -29 (0.033) and 127 (5.233) of normal
# if (theDialog->FindPaneByID(iIncreasedChanceToBlock)->GetValue()) 
# {
#     int iVal = ((int)(GetEditTextAsFloat(theDialog, iBlockChance) * 30.0) - 30);
#     terrain_costs[_terrain_steep] = PIN(iVal, -29, 127);
# }

# ---

# SetEditTextAsFloat(theDialog, iChargeSpeed, ((float)terrain_costs[_terrain_rocky] / 100.0f) + 1.0f, 3);
# // Non-positive speeds are set to 1.2 times.
# iVal = ((int)(GetEditTextAsFloat(theDialog, iChargeSpeed) * 100.0f) - 100);
# terrain_costs[_terrain_rocky] = PIN(iVal, 20, 127);

# ---

# SetEditTextAsShort(theDialog, iChargeRange, (terrain_costs[_terrain_snow] < 0) ? 0 : terrain_costs[_terrain_snow]);
# // Negative charge ranges have no effect
# int iVal = GetEditTextAsShort(theDialog, iChargeRange);
# terrain_costs[_terrain_snow] = PIN(iVal, 1, 127);

# ---

# SetEditTextAsShort(theDialog, iExperienceLimit, (unsigned char)terrain_costs[_terrain_marsh]);
# // Build 337 - HAR - Added vetting convenience field
# terrain_costs[_terrain_marsh] = (theDialog->FindPaneByID(iCanHasMoreExperience)->GetValue()) ? GetEditTextAsShort(theDialog, iExperienceLimit) : 0;

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
    ('52s', 'sequence_indexes', codec.list_pack('MonsSeqIndexes', 26, '>h')),
    ('4s', 'burning_death_projectile_group_tag'),
    ('h', 'burning_death_projectile_group_type'),
    ('B', 'experience_kill_bonus'),
    ('B', 'experience_bonus_radius'),
    ('H', 'propelled_system_shock'),
    ('H', 'damage_to_propulsion'),
    ('16s', 'terrain_costs', codec.codec(MonsTerrainCostsFmt)),
    ('H', 'terrain_impassability_flags'), # set at runtime
    ('h', 'pathfinding_radius'),
    ('16s', 'movement_modifiers', codec.codec(MonsMovementModsFmt)),
    ('H', 'absorbed_fraction', codec.Fixed),
    ('h', 'warning_distance'),
    ('h', 'critical_distance'),
    ('h', 'healing_fraction', codec.ShortPercent),
    ('h', 'initial_ammunition_lower_bound'),
    ('h', 'initial_ammunition_delta'),
    ('h', 'activation_distance'),
    ('2x', None),

    ('H', 'turning_speed', codec.AngularVelocity),
    ('h', 'base_movement_speed'),
    ('H', 'left_handed_fraction'),
    ('h', 'size', Size),
    ('4s', 'object_tag'),
    ('h', 'number_of_attacks'),
    ('h', 'desired_projectile_volume'),
    ('256s', 'attacks', codec.list_codec(
        MAX_ATTACKS, AttackDefFmt,
        filter_fun=lambda self, attack: not codec.all_off(attack.projectile_tag)
    )),
    ('4s', 'map_action_tag'),
    ('h', 'attack_frequency_lower_bound', codec.Simple),
    ('h', 'attack_frequency_delta', codec.delta('attack_frequency_lower_bound')),
    ('4s', 'exploding_projectile_group_tag'),
    ('h', 'hack_flags'),
    ('h', 'maximum_ammunition_count'),
    ('H', 'hard_death_system_shock'),
    ('H', 'flinch_system_shock', codec.Fixed),
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
    ('40s', 'sound_tags', codec.list_pack(
        'MonsSoundTags', 10, '>4s',
        filter_fun=lambda self, tag: not codec.all_on(tag),
        empty_value=struct.pack('>l', -1)
    )),
    ('4s', 'blocked_impact_projectile_group_tag'),
    ('4s', 'absorbed_impact_projectile_group_tag'),
    ('4s', 'ammunition_projectile_tag'),
    ('h', 'visibility_type'),
    ('h', 'combined_power'),
    ('h', 'longest_range', codec.World),
    ('h', 'cost'),
    ('10s', 'sound_types', codec.list_pack('MonsSoundTypes', 10, '>b')),
    ('h', 'enemy_experience_kill_bonus'),
    ('4s', 'entrance_projectile_group_tag'),
    ('4s', 'local_projectile_group_tag'),
    ('4s', 'special_ability_string_list_tag'),
    ('4s', 'exit_projectile_group_tag'),
    ('h', 'maximum_mana', codec.ShortFixed),
    ('h', 'mana_recharge_rate', codec.ShortFixed),
    ('H', 'berserk_system_shock', codec.Fixed),
    ('H', 'berserk_vitality', codec.Fixed),
    ('h', 'maximum_artifacts_carried'),
    ('2x', None),
    ('4s', 'initial_artifacts_projectile_group_tag'),
    ('L', 'extra_flags', MonsExtraFlag),
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
    ('h', 'slashing_damage', codec.ShortFixed),
    ('h', 'kinetic_damage', codec.ShortFixed),
    ('h', 'explosive_damage', codec.ShortFixed),
    ('h', 'electric_damage', codec.ShortFixed),
    ('h', 'fire_damage', codec.ShortFixed),
    ('h', 'paralysis_duration', codec.ShortFixed),
    ('h', 'stone', codec.ShortFixed),
    ('h', 'gas_damage', codec.ShortFixed),
    ('h', 'confusion', codec.ShortFixed),
    ('14x', None),
])

UnitTagFmt = ('UnitTag', [
    ('4s', 'mons'),
    ('4s', 'core'),
])

ObjeTagFmt = ('ObjeTag', [
    ('h', 'flags', ObjeFlags),
    ('h', 'gravity', codec.World),
    ('h', 'elasticity', codec.ShortFixed),
    ('h', 'terminal_velocity', codec.World),
    ('h', 'vitality_lower_bound', codec.ShortFixed),
    ('h', 'vitality_delta', codec.short_fixed_delta('vitality_lower_bound')),
    ('h', 'scale_lower_bound', codec.ShortFixed),
    ('h', 'scale_delta', codec.short_fixed_delta('scale_lower_bound')),
    ('32s', 'effect_modifiers', codec.codec(ObjeEffectFmt)),
    ('h', 'minimum_damage', codec.ShortFixed),
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
    ('16s', 'projectile_tags', codec.list_pack('ArtifactProjTags', MAX_ARTI_PROJ, '>4s')),
    ('L', 'bonus_monster_flags'),
    ('h', 'monster_override_type'),
    ('h', 'expiry_timer'),
    ('32s', 'bonus_effect_modifiers', codec.list_pack('ArtifactEffectMods', MAX_ARTI_EFFECT_MODS, '>h')),
    ('64s', 'override_attack', codec.codec(AttackDefFmt)),
    ('4s', 'special_ability_string_list_tag'),
    ('4s', 'monster_override_tag'),
    ('h', 'collection_index'),
    ('h', 'special_ability_string_list_index'),
    ('8s', 'projectile_types', codec.list_pack('ArtifactProjTypes', MAX_ARTI_PROJ, '>h')),
])

def sequence_name(idx):
    if idx < len(SequenceNames):
        return SequenceNames[idx]
    else:
        return ''

def parse_artifact(data):
    return myth_headers.parse_tag(ArtifactFmt, data)

def parse_unit(data):
    return myth_headers.parse_tag(UnitTagFmt, data)

def parse_obje(data):
    return myth_headers.parse_tag(ObjeTagFmt, data)

def parse_tag(data):
    return myth_headers.parse_tag(MonsTagFmt, data)

def encode_tag(tag_header, mons_tag):
    tag_data = mons_tag.value

    tag_data_size = len(tag_data)

    # Adjust tag header size
    new_tag_header = myth_headers.normalise_tag_header(
        tag_header,
        tag_data_size=tag_data_size
    )
    return (
        new_tag_header.value
        + tag_data
    )
