import itertools
from collections import defaultdict
from collections import namedtuple
from copy import copy
from copy import deepcopy
from abc import ABC
from abc import abstractmethod
import math

import constants
import logging
from config import ShowdownConfig

import data
from data import all_move_json
from data import pokedex
from data.parse_smogon_stats import MOVES_STRING
from data.parse_smogon_stats import SPREADS_STRING
from data.parse_smogon_stats import ABILITY_STRING
from data.parse_smogon_stats import ITEM_STRING
from data.helpers import get_pokemon_sets
from data.helpers import get_mega_pkmn_name
from data.helpers import PASS_ITEMS
from data.helpers import PASS_ABILITIES
from data.helpers import get_all_likely_moves
from data.helpers import get_most_likely_item
from data.helpers import get_most_likely_ability
from data.helpers import get_most_likely_spread
from data.helpers import get_all_possible_moves_for_random_battle

from showdown.engine.objects import State
from showdown.engine.objects import Side
from showdown.engine.objects import Pokemon as TransposePokemon

from showdown.engine.helpers import remove_duplicate_spreads
from showdown.engine.helpers import get_pokemon_info_from_condition
from showdown.engine.helpers import set_makes_sense
from showdown.engine.helpers import normalize_name
from showdown.engine.helpers import calculate_stats

from data import all_move_json as all_moves
from data import all_items_json as all_items
from showdown.engine.damage_calculator import pokemon_type_indicies

#from showdown.battle_bots.cnn.fusion import Fusion

logger = logging.getLogger(__name__)


LastUsedMove = namedtuple('LastUsedMove', ['pokemon_name', 'move', 'turn'])
DamageDealt = namedtuple('DamageDealt', ['attacker', 'defender', 'move', 'percent_damage', 'crit'])
StatRange = namedtuple("Range", ["min", "max"])


# Based on the format, this dict controls which pokemon will be replaced during team preview
# Some pokemon's forms are not revealed in team preview
smart_team_preview = {
    "gen8ou": {
        "urshifu": "urshifurapidstrike"  # urshifu banned in gen8ou
    }
}

def reverse_cantor(num: int):
    w = math.floor((math.sqrt(num * 8 + 1) - 1) / 2) #w and t are intermediary values
    t = int(((w + 1) * w) / 2)
    y = num - t
    x = w - y
    return (x,y) 

class Battle(ABC):

    def __init__(self, battle_tag):
        self.battle_tag = battle_tag
        self.user = Battler()
        self.opponent = Battler()
        self.weather = None
        self.field = None
        self.trick_room = False

        self.turn = False

        self.started = False
        self.rqid = None

        self.force_switch = False
        self.wait = False

        self.battle_type = None
        self.generation = None
        self.time_remaining = None

        self.request_json = None

    def initialize_team_preview(self, user_json, opponent_pokemon, battle_type):
        self.user.from_json(user_json, first_turn=True)
        self.user.reserve.insert(0, self.user.active)
        self.user.active = None

        for pkmn_string in opponent_pokemon:
            pokemon = Pokemon.from_switch_string(pkmn_string)

            if pokemon.name in smart_team_preview.get(battle_type, {}):
                new_pokemon_name = smart_team_preview[battle_type][pokemon.name]
                logger.info(
                    "Smart team preview: Replaced {} with {}".format(
                        pokemon.name,
                        new_pokemon_name
                    )
                )
                pokemon = Pokemon(new_pokemon_name, pokemon.level)

            self.opponent.reserve.append(pokemon)

        self.started = True
        self.rqid = user_json[constants.RQID]

    def during_team_preview(self):
        ...

    def start_non_team_preview_battle(self, user_json, opponent_switch_string):
        self.user.from_json(user_json, first_turn=True)

        pkmn_information = opponent_switch_string.split('|')[3]
        pkmn = Pokemon.from_switch_string(pkmn_information)
        self.opponent.active = pkmn

        self.started = True
        self.rqid = user_json[constants.RQID]

    def mega_evolve_possible(self):
        return (
                any(g in self.generation for g in constants.MEGA_EVOLVE_GENERATIONS) or
                'nationaldex' in ShowdownConfig.pokemon_mode
        )

    def prepare_battles(self, guess_mega_evo_opponent=True, join_moves_together=False):
        """Returns a list of battles based on this one
        The battles have the opponent's reserve pokemon's unknowns filled in
        The opponent's active pokemon in each of the battles has a different set"""
        battle_copy = deepcopy(self)
        battle_copy.opponent.lock_moves()
        battle_copy.user.lock_active_pkmn_first_turn_moves()

        if battle_copy.user.active.can_mega_evo:
            # mega-evolving here gives the pkmn the random-battle spread (Serious + 85s)
            # unfortunately the correct spread is not stored anywhere as of this being written
            # this only happens on the turn the pkmn mega-evolves - the next turn will be fine
            battle_copy.user.active.forme_change(get_mega_pkmn_name(battle_copy.user.active.name))

        if guess_mega_evo_opponent and not battle_copy.opponent.mega_revealed() and self.mega_evolve_possible():
            check_in_sets = battle_copy.battle_type == constants.STANDARD_BATTLE
            battle_copy.opponent.active.try_convert_to_mega(check_in_sets=check_in_sets)

        # for reserve pokemon only guess their most likely item/ability/spread and guess all moves
        for pkmn in filter(lambda x: x.is_alive(), battle_copy.opponent.reserve):
            pkmn.guess_most_likely_attributes()

        try:
            pokemon_sets = get_pokemon_sets(battle_copy.opponent.active.name)
        except KeyError:
            logger.warning("No sets for {}, trying to find most likely attributes".format(battle_copy.opponent.active.name))
            battle_copy.opponent.active.guess_most_likely_attributes()
            return [battle_copy]

        possible_spreads = sorted(pokemon_sets[SPREADS_STRING], key=lambda x: x[2], reverse=True)
        possible_abilities = sorted(pokemon_sets[ABILITY_STRING], key=lambda x: x[1], reverse=True)
        possible_items = sorted(pokemon_sets[ITEM_STRING], key=lambda x: x[1], reverse=True)
        possible_moves = sorted(pokemon_sets[MOVES_STRING], key=lambda x: x[1], reverse=True)

        spreads = battle_copy.opponent.active.get_possible_spreads(possible_spreads)
        items = battle_copy.opponent.active.get_possible_items(possible_items)
        abilities = battle_copy.opponent.active.get_possible_abilities(possible_abilities)
        expected_moves, chance_moves = battle_copy.opponent.active.get_possible_moves(possible_moves, battle_copy.battle_type)

        if join_moves_together:
            chance_move_combinations = [chance_moves]
        else:
            number_of_unknown_moves = max(4 - len(battle_copy.opponent.active.moves) - len(expected_moves), 0)
            chance_move_combinations = list(itertools.combinations(chance_moves, number_of_unknown_moves))

        combinations = list(itertools.product(spreads, items, abilities, chance_move_combinations))

        # create battle clones for each of the combinations
        battles = list()
        for c in combinations:
            new_battle = deepcopy(battle_copy)

            all_moves = [m.name for m in new_battle.opponent.active.moves]
            all_moves += expected_moves
            all_moves += c[3]
            all_moves = [Move(m) for m in all_moves]

            if join_moves_together or set_makes_sense(c[0][0], c[0][1], c[1], c[2], all_moves):
                new_battle.opponent.active.set_spread(c[0][0], c[0][1])
                if new_battle.opponent.active.name == 'ditto':
                    new_battle.opponent.active.stats = battle_copy.opponent.active.stats
                new_battle.opponent.active.item = c[1]
                new_battle.opponent.active.ability = c[2]
                for m in expected_moves:
                    new_battle.opponent.active.add_move(m)
                for m in c[3]:
                    new_battle.opponent.active.add_move(m)

                logger.debug("Possible set for opponent's {}:\t{} {} {} {} {}".format(battle_copy.opponent.active.name, c[0][0], c[0][1], c[1], c[2], all_moves))
                battles.append(new_battle)

            new_battle.opponent.lock_moves()

        return battles if battles else [battle_copy]

    def create_state(self):
        user_active = TransposePokemon.from_state_pokemon_dict(self.user.active.to_dict())
        user_reserve = dict()
        for mon in self.user.reserve:
            user_reserve[mon.name] = TransposePokemon.from_state_pokemon_dict(mon.to_dict())

        opponent_active = TransposePokemon.from_state_pokemon_dict(self.opponent.active.to_dict())
        opponent_reserve = dict()
        for mon in self.opponent.reserve:
            opponent_reserve[mon.name] = TransposePokemon.from_state_pokemon_dict(mon.to_dict())

        user = Side(user_active, user_reserve, copy(self.user.wish), copy(self.user.side_conditions), copy(self.user.future_sight))
        opponent = Side(opponent_active, opponent_reserve, copy(self.opponent.wish), copy(self.opponent.side_conditions), copy(self.opponent.future_sight))

        state = State(user, opponent, self.weather, self.field, self.trick_room)
        return state

    def get_all_options(self):
        force_switch = self.force_switch or self.user.active.hp <= 0
        wait = self.wait or self.opponent.active.hp <= 0

        # double faint or team preview
        if force_switch and wait:
            user_options = self.user.get_switches() or [constants.DO_NOTHING_MOVE]

            # edge-case for uturn or voltswitch killing
            if (
                    self.user.last_used_move.move in constants.SWITCH_OUT_MOVES and
                    self.opponent.active.hp <= 0 and
                    self.user.last_used_move.turn == self.turn

            ):
                opponent_options = [constants.DO_NOTHING_MOVE]
            else:
                opponent_options = self.opponent.get_switches() or [constants.DO_NOTHING_MOVE]

            return user_options, opponent_options

        if force_switch:
            user_options = self.user.get_switches(reviving=self.user.active.reviving)

            # uturn or voltswitch
            if (
                    self.user.last_used_move.move in constants.SWITCH_OUT_MOVES and
                    self.opponent.last_used_move.turn != self.turn and
                    self.user.last_used_move.turn == self.turn
            ):
                opponent_options = [m.name for m in self.opponent.active.moves if not m.disabled] or [constants.DO_NOTHING_MOVE]
            else:
                opponent_options = [constants.DO_NOTHING_MOVE]
        elif wait:
            opponent_options = self.opponent.get_switches()
            user_options = [constants.DO_NOTHING_MOVE]
        else:
            user_forced_move = self.user.active.forced_move()
            if user_forced_move:
                user_options = [user_forced_move]
            else:
                user_options = [m.name for m in self.user.active.moves if not m.disabled]
                user_options += self.user.get_switches()

            opponent_forced_move = self.opponent.active.forced_move()
            if opponent_forced_move:
                opponent_options = [opponent_forced_move]
            else:
                opponent_options = [m.name for m in self.opponent.active.moves if not m.disabled] or [constants.DO_NOTHING_MOVE]
                opponent_options += self.opponent.get_switches()

        return user_options, opponent_options

    @abstractmethod
    def find_best_move(self):
        ...


class Battler:

    def __init__(self):
        self.active = None
        self.reserve = []
        self.side_conditions = defaultdict(lambda: 0)

        self.name = None
        self.trapped = False
        self.wish = (0, 0)
        self.future_sight = (0, 0)

        self.account_name = None

        self.last_used_move = LastUsedMove('', '', 0)

    def mega_revealed(self):
        return self.active.is_mega or any(p.is_mega for p in self.reserve)

    def lock_active_pkmn_first_turn_moves(self):
        # disable firstimpression and fakeout if the last_used_move was not a switch
        if self.last_used_move.pokemon_name == self.active.name:
            for m in self.active.moves:
                if m.name in constants.FIRST_TURN_MOVES:
                    m.disabled = True

    def lock_active_pkmn_status_moves_if_active_has_assaultvest(self):
        if self.active.item == 'assaultvest':
            for m in self.active.moves:
                if all_move_json[m.name][constants.CATEGORY] == constants.STATUS:
                    m.disabled = True

    def choice_lock_moves(self):
        # if the active pokemon has a choice item and their last used move was by this pokemon -> lock their other moves
        if self.active.item in constants.CHOICE_ITEMS and self.last_used_move.pokemon_name == self.active.name:
            for m in self.active.moves:
                if m.name != self.last_used_move.move:
                    m.disabled = True

    def taunt_lock_moves(self):
        if constants.TAUNT in self.active.volatile_statuses:
            for m in self.active.moves:
                if all_move_json[m.name][constants.CATEGORY] == constants.STATUS:
                    m.disabled = True

    def lock_moves(self):
        self.choice_lock_moves()
        self.lock_active_pkmn_status_moves_if_active_has_assaultvest()
        self.lock_active_pkmn_first_turn_moves()
        self.taunt_lock_moves()

    def from_json(self, user_json, first_turn=False):

        # user_json does not track boosts or volatile statuses
        # they must be taken from the current battle
        if first_turn:
            existing_conditions = (None, None, None)
        else:
            existing_conditions = (
                self.active.name,
                self.active.boosts,
                self.active.volatile_statuses,
                self.active.terastallized,
                self.active.types
            )

        try:
            trapped = user_json[constants.ACTIVE][0].get(constants.TRAPPED, False)
            maybe_trapped = user_json[constants.ACTIVE][0].get(constants.MAYBE_TRAPPED, False)
            self.trapped = trapped or maybe_trapped
        except KeyError:
            self.trapped = False

        self.name = user_json[constants.SIDE][constants.ID]
        self.reserve.clear()
        for index, pkmn_dict in enumerate(user_json[constants.SIDE][constants.POKEMON]):

            nickname = pkmn_dict[constants.IDENT]
            pkmn = Pokemon.from_switch_string(pkmn_dict[constants.DETAILS], nickname=nickname)
            pkmn.ability = pkmn_dict[constants.REQUEST_DICT_ABILITY]
            pkmn.index = index + 1
            pkmn.reviving = pkmn_dict.get(constants.REVIVING, False)
            pkmn.hp, pkmn.max_hp, pkmn.status = get_pokemon_info_from_condition(pkmn_dict[constants.CONDITION])
            for stat, number in pkmn_dict[constants.STATS].items():
                pkmn.stats[constants.STAT_ABBREVIATION_LOOKUPS[stat]] = number

            pkmn.item = pkmn_dict[constants.ITEM] if pkmn_dict[constants.ITEM] else None

            if pkmn_dict[constants.ACTIVE]:
                self.active = pkmn
                if existing_conditions[0] == pkmn.name:
                    pkmn.boosts = existing_conditions[1]
                    pkmn.volatile_statuses = existing_conditions[2]
                    if existing_conditions[3]:
                        pkmn.terastallized = True
                        pkmn.types = existing_conditions[4]
            else:
                self.reserve.append(pkmn)

            for move_name in pkmn_dict[constants.MOVES]:
                pkmn.add_move(move_name)

        # if there is no active pokemon, we do not want to look through it's moves
        if constants.ACTIVE not in user_json:
            return

        try:
            self.active.can_mega_evo = user_json[constants.ACTIVE][0][constants.CAN_MEGA_EVO]
        except KeyError:
            self.active.can_mega_evo = False

        try:
            self.active.can_ultra_burst = user_json[constants.ACTIVE][0][constants.CAN_ULTRA_BURST]
        except KeyError:
            self.active.can_ultra_burst = False

        try:
            self.active.can_dynamax = user_json[constants.ACTIVE][0][constants.CAN_DYNAMAX]
        except KeyError:
            self.active.can_dynamax = False

        try:
            self.active.can_terastallize = user_json[constants.ACTIVE][0][constants.CAN_TERASTALLIZE]
        except KeyError:
            self.active.can_terastallize = False

        # clear the active moves so they can be reset by the options available
        self.active.moves.clear()

        # update the active pokemon's moves to show disabled status/pp remaining
        # this assumes that there is only one active pokemon (single-battle)
        for index, move in enumerate(user_json[constants.ACTIVE][0][constants.MOVES]):
            # hidden power's ID is always 'hiddenpower' regardless of the type
            # the type needs to be parsed separately from the 'move' attribute
            if move[constants.ID] == constants.HIDDEN_POWER:
                self.active.add_move('{}{}'.format(
                        constants.HIDDEN_POWER,
                        move['move'].split()[constants.HIDDEN_POWER_TYPE_STRING_INDEX].lower()
                    )
                )
            else:
                self.active.add_move(move[constants.ID])
            self.active.moves[-1].disabled = move.get(constants.DISABLED, False)
            self.active.moves[-1].current_pp = move.get(constants.PP, 1)

            try:
                self.active.moves[index].can_z = user_json[constants.ACTIVE][0][constants.CAN_Z_MOVE][index]
            except KeyError:
                pass

    def get_switches(self, reviving=False):
        if self.trapped:
            return []

        switches = []
        if reviving:
            it = filter(lambda p: p.hp <= 0, self.reserve)
        else:
            it = filter(lambda p: p.hp > 0, self.reserve)

        for pkmn in it:
            switches.append("{} {}".format(constants.SWITCH_STRING, pkmn.name))
        return switches

    def to_dict(self):
        return {
            constants.TRAPPED: self.trapped,
            constants.ACTIVE: self.active.to_dict(),
            constants.RESERVE: [p.to_dict() for p in self.reserve],
            constants.WISH: copy(self.wish),
            constants.FUTURE_SIGHT: copy(self.future_sight),
            constants.SIDE_CONDITIONS: copy(self.side_conditions)
        }


class Pokemon:

    def __init__(self, name: str, level: int, nature="serious", evs=(85,) * 6):
        self.name = normalize_name(name)
        self.nickname = None
        self.base_name = self.name
        self.level = level
        self.nature = nature
        self.evs = evs
        self.speed_range = StatRange(min=0, max=float("inf"))

        try:
            self.base_stats = pokedex[self.name][constants.BASESTATS]
        except KeyError:
            logger.info("Could not pokedex entry for {}".format(self.name))
            self.name = [k for k in pokedex if self.name.startswith(k)][0]
            logger.info("Using {} instead".format(self.name))
            self.base_stats = pokedex[self.name][constants.BASESTATS]

        self.stats = calculate_stats(self.base_stats, self.level, nature=nature, evs=evs)

        self.max_hp = self.stats.pop(constants.HITPOINTS)
        self.hp = self.max_hp
        if self.name == 'shedinja':
            self.max_hp = 1
            self.hp = 1

        self.ability = None
        self.types = pokedex[self.name][constants.TYPES]
        self.item = constants.UNKNOWN_ITEM

        self.terastallized = False
        self.fainted = False
        self.reviving = False
        self.moves = []
        self.status = None
        self.volatile_statuses = []
        self.boosts = defaultdict(lambda: 0)
        self.can_mega_evo = False
        self.can_ultra_burst = False
        self.can_dynamax = False
        self.is_mega = False
        self.can_have_assaultvest = True
        self.can_have_choice_item = True
        self.can_not_have_band = False
        self.can_not_have_specs = False
        self.can_have_life_orb = True
        self.can_have_heavydutyboots = True

    def forme_change(self, new_pkmn_name):
        hp_percent = float(self.hp) / self.max_hp
        moves = self.moves
        boosts = self.boosts
        status = self.status

        self.__init__(new_pkmn_name, self.level)
        self.hp = round(hp_percent * self.max_hp)
        self.moves = moves
        self.boosts = boosts
        self.status = status

    def try_convert_to_mega(self, check_in_sets=False):
        if self.item != constants.UNKNOWN_ITEM:
            return
        mega_pkmn_name = get_mega_pkmn_name(self.name)
        in_sets_data = mega_pkmn_name in data.pokemon_sets

        if (mega_pkmn_name and check_in_sets and in_sets_data) or (mega_pkmn_name and not check_in_sets):
            logger.debug("Guessing mega-evolution: {}".format(mega_pkmn_name))
            self.forme_change(mega_pkmn_name)

    def is_alive(self):
        return self.hp > 0

    @classmethod
    def extract_nickname_from_pokemonshowdown_string(cls, ps_string):
        return "".join(ps_string.split(":")[1:]).strip()

    @classmethod
    def from_switch_string(cls, switch_string, nickname=None):
        if nickname is not None:
            nickname = cls.extract_nickname_from_pokemonshowdown_string(nickname)

        details = switch_string.split(',')
        name = details[0]
        try:
            level = int(details[1].replace('L', '').strip())
        except (IndexError, ValueError):
            level = 100
        if "fusion" in details[-1]:
            pkmn = Fusion()
            pkmn.set_head(name)
            pkmn.set_body((details[-1])[details[-1].find(' ',2)+1:])
            pkmn.update_info()
        else:
            pkmn = Pokemon(name, level)
        pkmn.nickname = nickname
        return pkmn

    def set_spread(self, nature, evs):
        if isinstance(evs, str):
            evs = [int(e) for e in evs.split(',')]
        hp_percent = self.hp / self.max_hp
        self.stats = calculate_stats(self.base_stats, self.level, evs=evs, nature=nature)
        self.nature = nature
        self.evs = evs
        self.max_hp = self.stats.pop(constants.HITPOINTS)
        self.hp = round(self.max_hp * hp_percent)

    def add_move(self, move_name: str):
        try:
            new_move = Move(move_name)
            self.moves.append(new_move)
            return new_move
        except KeyError:
            logger.warning("{} is not a known move".format(move_name))
            return None

    def get_move(self, move_name: str):
        for m in self.moves:
            if m.name == normalize_name(move_name):
                return m
        return None

    def set_likely_moves_unless_revealed(self):
        if len(self.moves) == 4:
            return
        additional_moves = get_all_likely_moves(self.name, [m.name for m in self.moves])
        for m in additional_moves:
            self.moves.append(Move(m))

    def set_most_likely_ability_unless_revealed(self):
        if self.ability is not None:
            return
        ability = get_most_likely_ability(self.name)
        self.ability = ability

    def set_most_likely_item_unless_revealed(self):
        if self.item != constants.UNKNOWN_ITEM:
            return
        item = get_most_likely_item(self.name)
        self.item = item

    def set_most_likely_spread(self):
        nature, evs, _ = get_most_likely_spread(self.name)
        self.set_spread(nature, evs)

    def guess_most_likely_attributes(self):
        self.set_most_likely_ability_unless_revealed()
        self.set_most_likely_item_unless_revealed()
        self.set_likely_moves_unless_revealed()
        self.set_most_likely_spread()

    def get_possible_spreads(self, spreads):
        # update this once you can use previous attacks to rule out spreads
        cumulative_percentage = 0
        possible_spreads = []
        for s in spreads:
            cumulative_percentage += s[2]
            possible_spreads.append(s[:2])
            if s[2] < 20 or cumulative_percentage >= 80:
                break

        return remove_duplicate_spreads(possible_spreads)

    def get_possible_items(self, items):
        # a bunch of flags could be set by the logic in the `battle_modifier` module
        # these flags being set render some items not possible
        # for example, if a pkmn uses 2 different moves without switching, then 'can_have_choice_item' will be False
        # this will omit choice items when guessing an item

        if self.item == constants.UNKNOWN_ITEM:
            cumulative_percentage = 0
            possible_items = []
            for i in items:
                if i[1] < 10 or cumulative_percentage >= 80:
                    return possible_items if possible_items else [constants.UNKNOWN_ITEM]
                elif i[0] in constants.CHOICE_ITEMS and not self.can_have_choice_item:
                    pass
                elif i[0] == 'lifeorb' and not self.can_have_life_orb:
                    pass
                elif i[0] == 'assaultvest' and not self.can_have_assaultvest:
                    pass
                elif i[0] == 'heavydutyboots' and not self.can_have_heavydutyboots:
                    pass
                elif i[0] == 'choiceband' and self.can_not_have_band:
                    pass
                elif i[0] == 'choicespecs' and self.can_not_have_specs:
                    pass
                elif i[0] not in PASS_ITEMS:
                    possible_items.append(i[0])

                cumulative_percentage += i[1]

            return possible_items if possible_items else [constants.UNKNOWN_ITEM]

        else:
            return [self.item]

    def get_possible_abilities(self, abilities):
        if self.ability is None:
            cumulative_percentage = 0
            possible_abilities = []
            for i in abilities:
                if i[1] < 10 or cumulative_percentage >= 80:
                    return possible_abilities if possible_abilities else [None]
                elif i[0] not in PASS_ABILITIES:
                    possible_abilities.append(i[0])

                cumulative_percentage += i[1]

            return possible_abilities if possible_abilities else [None]
        else:
            return [self.ability]

    def get_possible_moves(self, moves, battle_type=constants.STANDARD_BATTLE):
        if battle_type == constants.RANDOM_BATTLE:
            if len(self.moves) == 4:
                return [], []
            known_move_names = [m.name for m in self.moves]
            return [], get_all_possible_moves_for_random_battle(self.name, known_move_names)

        moves_remaining = 4 - len(self.moves)
        expected_moves = list()
        chance_moves = list()

        for m in moves:
            if moves_remaining <= 0:
                break
            elif m[1] > 60 and self.get_move(m[0]) is None:
                expected_moves.append(m[0])
                moves_remaining -= 1
            elif m[1] > 20 and self.get_move(m[0]) is None:
                chance_moves.append(m[0])

        return expected_moves, chance_moves

    def forced_move(self):
        if "phantomforce" in self.volatile_statuses:
            return "phantomforce"
        elif "shadowforce" in self.volatile_statuses:
            return "shadowforce"
        elif "dive" in self.volatile_statuses:
            return "dive"
        elif "dig" in self.volatile_statuses:
            return "dig"
        elif "bounce" in self.volatile_statuses:
            return "bounce"
        elif "fly" in self.volatile_statuses:
            return "fly"
        else:
            return None

    def to_dict(self):
        return {
            constants.FAINTED: self.fainted,
            constants.ID: self.name,
            constants.LEVEL: self.level,
            constants.TYPES: self.types,
            constants.HITPOINTS: self.hp,
            constants.MAXHP: self.max_hp,
            constants.ABILITY: self.ability,
            constants.ITEM: self.item,
            constants.BASESTATS: self.base_stats,
            constants.STATS: self.stats,
            constants.NATURE: self.nature,
            constants.EVS: self.evs,
            constants.BOOSTS: self.boosts,
            constants.STATUS: self.status,
            constants.TERASTALLIZED: self.terastallized,
            constants.VOLATILE_STATUS: set(self.volatile_statuses),
            constants.MOVES: [m.to_dict() for m in self.moves]
        }

    @classmethod
    def get_dummy(cls):
        p = Pokemon('pikachu', 100)
        p.hp = 0
        p.name = ''
        p.ability = None
        p.fainted = True
        return p

    def __eq__(self, other):
        return self.name == other.name and self.level == other.level

    def __repr__(self):
        return "{}, level {}".format(self.name, self.level)


class Move:
    def __init__(self, name):
        name = normalize_name(name)
        if constants.HIDDEN_POWER in name and not name.endswith(constants.HIDDEN_POWER_ACTIVE_MOVE_BASE_DAMAGE_STRING):
            name = "{}{}".format(name, constants.HIDDEN_POWER_ACTIVE_MOVE_BASE_DAMAGE_STRING)
        move_json = all_move_json[name]
        self.name = name
        self.max_pp = int(move_json.get(constants.PP) * 1.6)

        self.disabled = False
        self.can_z = False
        self.current_pp = self.max_pp

    def to_dict(self):
        return {
            "id": self.name,
            "disabled": self.disabled,
            "current_pp": self.current_pp
        }

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return "{}".format(self.name)
    
class Fusion(Pokemon):    
    non_volatie_to_num = { #0 is healthy, but there's no constant for that
        '' : 0,
        constants.SLEEP : 1,
        constants.BURN : 2,
        constants.FROZEN : 3,
        constants.PARALYZED : 4,
        constants.POISON : 5,
        constants.TOXIC : 6
    }
    
    @classmethod
    def from_pokemon(cls,base : Pokemon):
        if base.name != '':
            output = Fusion(base.name)
        else:
            output = Fusion()
        return output
    
    def __init__(self,head = "aggron"):
        super().__init__(head,100)
        super().set_likely_moves_unless_revealed()
        self.fusion_id = 0
        self.body = None
        self.set_head(head)
        self.potential_abilities = []
        self.ability = -1
        self.item = None
        self.hpPercent = 100
        self.types = [18,18,18,18] #list instead of 2 vars cause of the triple fusions (screw you Zapmolticuno)
        self.non_volatile_status = ''
        
    def update_info(self): #also updates typing
        if (self.head is None):
            raise ValueError("Set Fusion fusion_id or Head before updating info")
        self.types = []
        self.update_id()
        if not (self.body is None):
            self.stats[constants.HITPOINTS] = math.floor((self.body['baseStats'][constants.HITPOINTS] / 3) + 2 * (self.head['baseStats'][constants.HITPOINTS] / 3))
            self.stats[constants.ATTACK] = math.floor((2 * (self.body['baseStats'][constants.ATTACK] / 3)) + (self.head['baseStats'][constants.ATTACK]/3))
            self.stats[constants.SPECIAL_ATTACK] = math.floor((self.body['baseStats'][constants.SPECIAL_ATTACK] / 3) + 2 * (self.head['baseStats'][constants.SPECIAL_ATTACK] / 3))
            self.stats[constants.DEFENSE] = math.floor((2 * (self.body['baseStats'][constants.DEFENSE] / 3)) + (self.head['baseStats'][constants.DEFENSE]/3))
            self.stats[constants.SPECIAL_DEFENSE] = math.floor((self.body['baseStats'][constants.SPECIAL_DEFENSE] / 3) + 2 * (self.head['baseStats'][constants.SPECIAL_DEFENSE] / 3))
            self.stats[constants.SPEED] = math.floor((2 * (self.body['baseStats'][constants.SPEED] / 3) )+ (self.head['baseStats'][constants.SPEED]/3))
            self.types.append(self.head["types"][0])
            if len(self.body["types"]) == 1:
                if not (self.body["types"][0] is self.head["types"][0]):
                    self.types.append(self.body["types"][0])
                else:
                    self.types.append("typeless") #Ho-Oh/Entei is fire type
            else:
                self.types.append(self.body["types"][1])
            self.types.append('typeless')
            self.types.append('typeless')
            for ability_key in self.head["abilities"]:
                self.potential_abilities.append(normalize_name(self.head["abilities"][ability_key]))
            for ability_key in self.body["abilities"]:
                self.potential_abilities.append(normalize_name(self.body["abilities"][ability_key]))
        else:
            self.stats = copy(self.head["baseStats"])
            self.types.append(self.head["types"][0])
            try:
                self.types.append(self.head["types"][1])
            except IndexError:
                self.types.append("typeless")
            self.types.append("typeless")
            self.types.append("typeless")
            for ability_key in self.head["abilities"]:
                self.potential_abilities.append(normalize_name(self.head["abilities"][ability_key]))
        self.max_hp = self.stats.pop(constants.HITPOINTS)
        self.hp = self.max_hp
            
        
    def set_head(self,newHead : str):
        self.name = normalize_name(newHead)
        self.base_name = self.name
        self.head = pokedex[self.name]
        

    def set_body(self,newBody : str):
        self.body = pokedex[normalize_name(newBody)]
    
    def set_item(self,item_name):
        for item in all_items:
            if all_items[item]["name"] == item_name:
                self.item = item
                break

    def set_status(self,status):
        for non_vol in constants.NON_VOLATILE_STATUSES:
            if non_vol == status:
                self.non_volatile_status = non_vol

    def as_input(self): #if fusion_id not set, set with Cantor pairing function
        output = str(self.fusion_id) + ","
        for type in self.types:
            output += str(pokemon_type_indicies[type]) + ","
        output += str(self.max_hp) + ","
        for stat_name in self.stats:
            output += str(self.stats[stat_name]) + ","
        for idx, move_name in enumerate(self.moves[:4]):
            counter = 1
            for move in all_moves:
                if normalize_name(all_moves[move]["name"]) == move_name.name:
                    output += str(counter) + ","
                    break
                counter += 1
        if self.ability in self.potential_abilities:
            output += str(self.potential_abilities.index(self.ability) + 1) + ","
        else:
            output += "-1,"
        output += str(self.hpPercent) + ","
        if self.item is None:
            output += "0,"
        else:
            output += str(all_items[self.item]["num"]) + ","
        output += str(Fusion.non_volatie_to_num[self.non_volatile_status]) + ","
        return output

    @staticmethod
    def input_key():
        return [
                "fusion_id",
                "type1",
                "type2",
                "type3",
                "type4",
                constants.HITPOINTS,
                constants.ATTACK,
                constants.SPECIAL_ATTACK,
                constants.DEFENSE,
                constants.SPECIAL_DEFENSE,
                constants.SPEED,
                "move1",
                "move2",
                "move3",
                "move4",
                "ability",
                "hpPercent",
                "item",
                "status"
            ]
    
    def set_fusion(self,newId):
        self.fusion_id = newId
        head_num, body_num = reverse_cantor(newId)
        for pokemon in pokedex:
            if pokedex[pokemon]["num"] == body_num:
                self.body = pokedex[pokemon]
            if pokedex[pokemon]["num"] == head_num:
                self.head = pokedex[pokemon]
            if not (self.body is None or self.head is None) and self.head["num"] == head_num and self.body["num"] == body_num:
                break
            
    def update_id(self):
        if not(self.head is None):
            if not (self.body is None):
                self.fusion_id = int(0.5 * (self.head["num"] + self.body["num"]) * (self.head["num"] + self.body["num"] + 1) + self.body["num"])
            else:
                self.fusion_id = -self.head["num"]
        else:
            self.fusion_id = 0
            
    def is_alive(self):
        return self.hpPercent > 0
    

class Triple_Fusion(Fusion):
    def __init__(self):
        self.mid = None
        super().__init__()
        
    def set_fusion(self, newId):
        main_fusion_num, mid_num = reverse_cantor(newId)
        for pokemon in pokedex:
            if pokedex[pokemon]["num"] == mid_num:
                self.mid = pokemon
                break
        super().set_fusion(main_fusion_num)
        self.fusion_id = newId
    
    def update_info(self):
        if self.fusion_id == 0:
            raise ValueError("Triple Fusion fusion_id not set, please set fusion_id before updaing info")
        elif self.fusion_id == 7118213831: #Enraicune
            self.types = ["fire","water","electric"]
            self.stats[constants.HITPOINTS] = 102
            self.stats[constants.ATTACK] = 92
            self.stats[constants.DEFENSE] = 92
            self.stats[constants.SPECIAL_ATTACK] = 98
            self.stats[constants.SPECIAL_DEFENSE] = 97
            self.stats[constants.SPEED] = 100
            self.potential_abilities = ["Inner Focus", "Pressure"]
        elif self.fusion_id == 97322323090: #Celemewchi
            self.types = ["psychic","steel","grass","typeless"]
            self.stats[constants.HITPOINTS] = 100
            self.stats[constants.ATTACK] = 100
            self.stats[constants.DEFENSE] = 100
            self.stats[constants.SPECIAL_ATTACK] = 100
            self.stats[constants.SPECIAL_DEFENSE] = 100
            self.stats[constants.SPEED] = 100
            self.potential_abilities = ["Synchronize","Natural Cure","Serene Grace"]
        elif self.fusion_id == 40940196257: #Regitrio
            self.types = ["ice","rock","steel","typeless"]
            self.stats[constants.HITPOINTS] = 80
            self.stats[constants.ATTACK] = 100
            self.stats[constants.DEFENSE] = 200
            self.stats[constants.SPECIAL_ATTACK] = 100
            self.stats[constants.SPECIAL_DEFENSE] = 200
            self.stats[constants.SPEED] = 50
            self.potential_abilities = ["Clear Body"]
        elif self.fusion_id == 914914620: #Zapmolticuno
            self.types = ["flying","ice","fire","electric"]
            self.stats[constants.HITPOINTS] = 90
            self.stats[constants.ATTACK] = 100
            self.stats[constants.DEFENSE] = 100
            self.stats[constants.SPECIAL_ATTACK] = 125
            self.stats[constants.SPECIAL_DEFENSE] = 125
            self.stats[constants.SPEED] = 100
            self.potential_abilities = ["Serene Grace","Pressure"]
        else:
            self.types = ["fire","water","grass","typeless"]
            if self.fusion_id == 8826753668: #Swamptiliken
                self.stats[constants.HITPOINTS] = 100
                self.stats[constants.ATTACK] = 120
                self.stats[constants.DEFENSE] = 90
                self.stats[constants.SPECIAL_ATTACK] = 110
                self.stats[constants.SPECIAL_DEFENSE] = 90
                self.stats[constants.SPEED] = 120
                self.potential_abilities = ["Unburden","Speed Boost","Damp"]
            elif self.fusion_id == 46866513956: #Torterneon
                self.stats[constants.HITPOINTS] = 95
                self.stats[constants.ATTACK] = 109
                self.stats[constants.DEFENSE] = 105
                self.stats[constants.SPECIAL_ATTACK] = 111
                self.stats[constants.SPECIAL_DEFENSE] = 101
                self.stats[constants.SPEED] = 108
                self.potential_abilities = ["Shell Armor","Iron Fist","Defiant"]
            elif self.fusion_id == 1238651035: #Megaligasion
                self.stats[constants.HITPOINTS] = 85
                self.stats[constants.ATTACK] = 105
                self.stats[constants.DEFENSE] = 100
                self.stats[constants.SPECIAL_ATTACK] = 109
                self.stats[constants.SPECIAL_DEFENSE] = 100
                self.stats[constants.SPEED] = 100
                self.potential_abilities = ["Leaf Guard","Flash Fire","Sheer Force"]
            elif self.fusion_id == 4377: #Venustoizard
                self.stats[constants.HITPOINTS] = 80
                self.stats[constants.ATTACK] = 84
                self.stats[constants.DEFENSE] = 100
                self.stats[constants.SPECIAL_ATTACK] = 109
                self.stats[constants.SPECIAL_DEFENSE] = 105
                self.stats[constants.SPEED] = 100
                self.potential_abilities = ["Chlorophyll","Solar Power","Rain Dish"]
            elif self.fusion_id == 1162126314: #Baylavanaw
                self.stats[constants.HITPOINTS] = 65
                self.stats[constants.ATTACK] = 80
                self.stats[constants.DEFENSE] = 80
                self.stats[constants.SPECIAL_ATTACK] = 80
                self.stats[constants.SPECIAL_DEFENSE] = 80
                self.stats[constants.SPEED] = 80
                self.potential_abilities = ["Leaf Guard","Flash Fire","Sheer Force"]
            elif self.fusion_id == 8691354502: #Gromarshken
                self.stats[constants.HITPOINTS] = 70
                self.stats[constants.ATTACK] = 85
                self.stats[constants.DEFENSE] = 70
                self.stats[constants.SPECIAL_ATTACK] = 85
                self.stats[constants.SPECIAL_DEFENSE] = 70
                self.stats[constants.SPEED] = 95
                self.potential_abilities = ["Unburden","Speed Boost","Damp"]
            elif self.fusion_id == 869: #Ivymelortle
                self.stats[constants.HITPOINTS] = 60
                self.stats[constants.ATTACK] = 64
                self.stats[constants.DEFENSE] = 80
                self.stats[constants.SPECIAL_ATTACK] = 80
                self.stats[constants.SPECIAL_DEFENSE] = 80
                self.stats[constants.SPEED] = 80
                self.potential_abilities = ["Chlorophyll","Solar Power","Rain Dish"]
            elif self.fusion_id == 47828451358: #Prinfernotle
                self.stats[constants.HITPOINTS] = 75
                self.stats[constants.ATTACK] = 89
                self.stats[constants.DEFENSE] = 85
                self.stats[constants.SPECIAL_ATTACK] = 81
                self.stats[constants.SPECIAL_DEFENSE] = 76
                self.stats[constants.SPEED] = 81
                self.potential_abilities = ["Shell Armor","Iron Fist","Defiant"]
            elif self.fusion_id == 358: #Bulbmantle
                self.stats[constants.HITPOINTS] = 45
                self.stats[constants.ATTACK] = 52
                self.stats[constants.DEFENSE] = 65
                self.stats[constants.SPECIAL_ATTACK] = 65
                self.stats[constants.SPECIAL_DEFENSE] = 65
                self.stats[constants.SPEED] = 65
                self.potential_abilities = ["Chlorophyll","Solar Power","Rain Dish"]
            elif self.fusion_id == 8758460028: #Torkipcko
                self.stats[constants.HITPOINTS] = 50
                self.stats[constants.ATTACK] = 70
                self.stats[constants.DEFENSE] = 50
                self.stats[constants.SPECIAL_ATTACK] = 70
                self.stats[constants.SPECIAL_DEFENSE] = 55
                self.stats[constants.SPEED] = 70
                self.potential_abilities = ["Unburden","Speed Boost","Damp"]
            elif self.fusion_id == 1176731483: #Totoritaquil
                self.stats[constants.HITPOINTS] = 50
                self.stats[constants.ATTACK] = 65
                self.stats[constants.DEFENSE] = 65
                self.stats[constants.SPECIAL_ATTACK] = 60
                self.stats[constants.SPECIAL_DEFENSE] = 65
                self.stats[constants.SPEED] = 65
                self.potential_abilities = ["Leaf Guard","Flash Fire","Sheer Force"]
            elif self.fusion_id == 45915560559: #Turcharlup
                self.stats[constants.HITPOINTS] = 55
                self.stats[constants.ATTACK] = 68
                self.stats[constants.DEFENSE] = 64
                self.stats[constants.SPECIAL_ATTACK] = 61
                self.stats[constants.SPECIAL_DEFENSE] = 56
                self.stats[constants.SPEED] = 61
                self.potential_abilities = ["Shell Armor","Iron Fist","Defiant"]
