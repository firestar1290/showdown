from typing import Any
import math

from sys import path

path.append("")

from data import pokedex
from data import all_move_json as all_moves
from data import all_items_json as all_items
from showdown.engine.damage_calculator import pokemon_type_indicies
import constants
    
def reverse_cantor(num: int):
    w = math.floor((math.sqrt(num * 8 + 1) - 1) / 2) #w and t are intermediary values
    t = int(((w + 1) * w) / 2)
    y = num - t
    x = w - y
    return (x,y)    

class Fusion():    
    non_volatie_to_num = { #0 is healthy, but there's no constant for that
        '' : 0,
        constants.SLEEP : 1,
        constants.BURN : 2,
        constants.FROZEN : 3,
        constants.PARALYZED : 4,
        constants.POISON : 5,
        constants.TOXIC : 6
    }
    
    def __init__(self):
        self.id = 0
        self.body = None
        self.head = None
        self.potential_abilities = []
        self.ability = -1
        self.item = None
        self.stats = {
            constants.HITPOINTS : 0,
            constants.ATTACK : 0,
            constants.DEFENSE : 0,
            constants.SPECIAL_ATTACK : 0,
            constants.SPECIAL_DEFENSE : 0,
            constants.SPEED : 0
        }
        self.hpPercent = 100
        self.moves = {
            1 : '',
            2 : '',
            3 : '',
            4 : ''
        }
        self.types = [] #list instead of 2 vars cause of the triple fusions
        self.non_volatile_status = ''
        
    def update_info(self): #also updates typing
        if (self.head is None):
            raise ValueError("Set Fusion ID or Head and Body before updating info")
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
                self.potential_abilities.append(self.head["abilities"][ability_key])
            for ability_key in self.body["abilities"]:
                self.potential_abilities.append(self.body["abilities"][ability_key])
        else:
            self.stats = self.head["baseStats"]
            self.types.append(self.head["types"][0])
            try:
                self.types.append(self.head["types"][1])
            except IndexError:
                self.types.append("typeless")
            self.types.append("typeless")
            self.types.append("typeless")
            for ability_key in self.head["abilities"]:
                self.potential_abilities.append(self.head["abilities"][ability_key])
            
        
    def set_head(self,newHead : str):
        try:
            self.head = pokedex[newHead]
        except KeyError:
            if newHead == "porygon-z":
                self.head = pokedex["porygonz"]
            elif newHead[:8] == "oricorio":
                if newHead[9] == 'p':
                    if newHead[10] == 'o':
                        self.head = pokedex["oricoriopompom"]
                    else:
                        self.head = pokedex["oricoriopau"]
                elif newHead[9] == 's':
                    self.head = pokedex["oricoriosensu"]
                else:
                    self.head = pokedex["oricorio"]
            elif newHead[:8] == "lycanroc":
                if newHead[9:] == "midnight":
                    self.head = pokedex["lycanrocmidnight"]
                elif newHead[9:] == "dusk":
                    self.head = pokedex["lycanrocdusk"]
                else:
                    self.head = pokedex["lycanroc"]
            elif newHead == "mr. mime":
                self.head = pokedex["mrmime"]

    def set_body(self,newBody : str):
        try:
            self.body = pokedex[newBody]
        except KeyError:
            if newBody == "porygon-z":
                self.body = pokedex["porygonz"]
            elif newBody[:8] == "oricorio":
                self.body = pokedex["oricorio"]
            elif newBody[:8] == "lycanroc":
                if newBody[9:] == "midnight":
                    self.body = pokedex["lycanrocmidnight"]
                elif newBody[9:] == "dusk":
                    self.body = pokedex["lycanrocdusk"]
                else:
                    self.body = pokedex["lycanroc"]
    
    def set_item(self,item_name):
        for item in all_items:
            if all_items[item]["name"] == item_name:
                self.item = item
                break

    def set_status(self,status):
        for non_vol in constants.NON_VOLATILE_STATUSES:
            if non_vol == status:
                self.non_volatile_status = non_vol

    def as_input(self): #if id not set, set with Cantor pairing function
        output = str(self.id) + ","
        for type in self.types:
            output += str(pokemon_type_indicies[type]) + ","
        for stat_name in self.stats:
            output += str(self.stats[stat_name]) + ","
        for idx in self.moves:
            if self.moves[idx] == '':
                output += "0,"
            else:
                counter = 1
                for move in all_moves:
                    if all_moves[move]["name"] == self.moves[idx]:
                        output += str(counter) + ","
                        break
                    counter += 1
        output += str(self.ability + 1) + ","
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
                "id",
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
        self.id = newId
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
                self.id = int(0.5 * (self.head["num"] + self.body["num"]) * (self.head["num"] + self.body["num"] + 1) + self.body["num"])
            else:
                self.id = -self.head["num"]
        else:
            self.id = 0
    

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
        self.id = newId
    
    def update_info(self):
        if self.id == 0:
            raise ValueError("Triple Fusion ID not set, please set ID before updaing info")
        elif self.id == 7118213831: #Enraicune
            self.types = ["fire","water","electric"]
            self.stats[constants.HITPOINTS] = 102
            self.stats[constants.ATTACK] = 92
            self.stats[constants.DEFENSE] = 92
            self.stats[constants.SPECIAL_ATTACK] = 98
            self.stats[constants.SPECIAL_DEFENSE] = 97
            self.stats[constants.SPEED] = 100
            self.potential_abilities = ["Inner Focus", "Pressure"]
        elif self.id == 97322323090: #Celemewchi
            self.types = ["psychic","steel","grass","typeless"]
            self.stats[constants.HITPOINTS] = 100
            self.stats[constants.ATTACK] = 100
            self.stats[constants.DEFENSE] = 100
            self.stats[constants.SPECIAL_ATTACK] = 100
            self.stats[constants.SPECIAL_DEFENSE] = 100
            self.stats[constants.SPEED] = 100
            self.potential_abilities = ["Synchronize","Natural Cure","Serene Grace"]
        elif self.id == 40940196257: #Regitrio
            self.types = ["ice","rock","steel","typeless"]
            self.stats[constants.HITPOINTS] = 80
            self.stats[constants.ATTACK] = 100
            self.stats[constants.DEFENSE] = 200
            self.stats[constants.SPECIAL_ATTACK] = 100
            self.stats[constants.SPECIAL_DEFENSE] = 200
            self.stats[constants.SPEED] = 50
            self.potential_abilities = ["Clear Body"]
        elif self.id == 914914620: #Zapmolticuno
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
            if self.id == 8826753668: #Swamptiliken
                self.stats[constants.HITPOINTS] = 100
                self.stats[constants.ATTACK] = 120
                self.stats[constants.DEFENSE] = 90
                self.stats[constants.SPECIAL_ATTACK] = 110
                self.stats[constants.SPECIAL_DEFENSE] = 90
                self.stats[constants.SPEED] = 120
                self.potential_abilities = ["Unburden","Speed Boost","Damp"]
            elif self.id == 46866513956: #Torterneon
                self.stats[constants.HITPOINTS] = 95
                self.stats[constants.ATTACK] = 109
                self.stats[constants.DEFENSE] = 105
                self.stats[constants.SPECIAL_ATTACK] = 111
                self.stats[constants.SPECIAL_DEFENSE] = 101
                self.stats[constants.SPEED] = 108
                self.potential_abilities = ["Shell Armor","Iron Fist","Defiant"]
            elif self.id == 1238651035: #Megaligasion
                self.stats[constants.HITPOINTS] = 85
                self.stats[constants.ATTACK] = 105
                self.stats[constants.DEFENSE] = 100
                self.stats[constants.SPECIAL_ATTACK] = 109
                self.stats[constants.SPECIAL_DEFENSE] = 100
                self.stats[constants.SPEED] = 100
                self.potential_abilities = ["Leaf Guard","Flash Fire","Sheer Force"]
            elif self.id == 4377: #Venustoizard
                self.stats[constants.HITPOINTS] = 80
                self.stats[constants.ATTACK] = 84
                self.stats[constants.DEFENSE] = 100
                self.stats[constants.SPECIAL_ATTACK] = 109
                self.stats[constants.SPECIAL_DEFENSE] = 105
                self.stats[constants.SPEED] = 100
                self.potential_abilities = ["Chlorophyll","Solar Power","Rain Dish"]
            elif self.id == 1162126314: #Baylavanaw
                self.stats[constants.HITPOINTS] = 65
                self.stats[constants.ATTACK] = 80
                self.stats[constants.DEFENSE] = 80
                self.stats[constants.SPECIAL_ATTACK] = 80
                self.stats[constants.SPECIAL_DEFENSE] = 80
                self.stats[constants.SPEED] = 80
                self.potential_abilities = ["Leaf Guard","Flash Fire","Sheer Force"]
            elif self.id == 8691354502: #Gromarshken
                self.stats[constants.HITPOINTS] = 70
                self.stats[constants.ATTACK] = 85
                self.stats[constants.DEFENSE] = 70
                self.stats[constants.SPECIAL_ATTACK] = 85
                self.stats[constants.SPECIAL_DEFENSE] = 70
                self.stats[constants.SPEED] = 95
                self.potential_abilities = ["Unburden","Speed Boost","Damp"]
            elif self.id == 869: #Ivymelortle
                self.stats[constants.HITPOINTS] = 60
                self.stats[constants.ATTACK] = 64
                self.stats[constants.DEFENSE] = 80
                self.stats[constants.SPECIAL_ATTACK] = 80
                self.stats[constants.SPECIAL_DEFENSE] = 80
                self.stats[constants.SPEED] = 80
                self.potential_abilities = ["Chlorophyll","Solar Power","Rain Dish"]
            elif self.id == 47828451358: #Prinfernotle
                self.stats[constants.HITPOINTS] = 75
                self.stats[constants.ATTACK] = 89
                self.stats[constants.DEFENSE] = 85
                self.stats[constants.SPECIAL_ATTACK] = 81
                self.stats[constants.SPECIAL_DEFENSE] = 76
                self.stats[constants.SPEED] = 81
                self.potential_abilities = ["Shell Armor","Iron Fist","Defiant"]
            elif self.id == 358: #Bulbmantle
                self.stats[constants.HITPOINTS] = 45
                self.stats[constants.ATTACK] = 52
                self.stats[constants.DEFENSE] = 65
                self.stats[constants.SPECIAL_ATTACK] = 65
                self.stats[constants.SPECIAL_DEFENSE] = 65
                self.stats[constants.SPEED] = 65
                self.potential_abilities = ["Chlorophyll","Solar Power","Rain Dish"]
            elif self.id == 8758460028: #Torkipcko
                self.stats[constants.HITPOINTS] = 50
                self.stats[constants.ATTACK] = 70
                self.stats[constants.DEFENSE] = 50
                self.stats[constants.SPECIAL_ATTACK] = 70
                self.stats[constants.SPECIAL_DEFENSE] = 55
                self.stats[constants.SPEED] = 70
                self.potential_abilities = ["Unburden","Speed Boost","Damp"]
            elif self.id == 1176731483: #Totoritaquil
                self.stats[constants.HITPOINTS] = 50
                self.stats[constants.ATTACK] = 65
                self.stats[constants.DEFENSE] = 65
                self.stats[constants.SPECIAL_ATTACK] = 60
                self.stats[constants.SPECIAL_DEFENSE] = 65
                self.stats[constants.SPEED] = 65
                self.potential_abilities = ["Leaf Guard","Flash Fire","Sheer Force"]
            elif self.id == 45915560559: #Turcharlup
                self.stats[constants.HITPOINTS] = 55
                self.stats[constants.ATTACK] = 68
                self.stats[constants.DEFENSE] = 64
                self.stats[constants.SPECIAL_ATTACK] = 61
                self.stats[constants.SPECIAL_DEFENSE] = 56
                self.stats[constants.SPEED] = 61
                self.potential_abilities = ["Shell Armor","Iron Fist","Defiant"]
        
    
        
    
        
