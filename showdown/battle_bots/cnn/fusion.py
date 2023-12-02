from typing import Any
import constants
import math

from data import pokedex
from engine.damage_calculator import type_effectiveness_modifier
    
class Fusion():    
    def __init__(self):
        self.id = 0
        self.body = None
        self.head = None
        self.ability = ''
        self.item = ''
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
        self.boosts = self.stats
        self.type1 = ""
        self.type2 = ""
        
    def update_type(self): #also updates typing
        if (self.body is None or self.head is None):
            return
        #not deleted for archiving purposes
        #self.stats[constants.HITPOINTS] = math.floor((self.body['baseStats'][constants.HITPOINTS] / 3) + 2 * (self.head['baseStats'][constants.HITPOINTS] / 3))
        #self.stats[constants.ATTACK] = math.floor((2 * (self.body['baseStats'][constants.ATTACK] / 3)) + (self.head['baseStats'][constants.ATTACK]/3))
        #self.stats[constants.SPECIAL_ATTACK] = math.floor((self.body['baseStats'][constants.SPECIAL_ATTACK] / 3) + 2 * (self.head['baseStats'][constants.SPECIAL_ATTACK] / 3))
        #self.stats[constants.DEFENSE] = math.floor((2 * (self.body['baseStats'][constants.DEFENSE] / 3)) + (self.head['baseStats'][constants.DEFENSE]/3))
        #self.stats[constants.SPECIAL_DEFENSE] = math.floor((self.body['baseStats'][constants.SPECIAL_DEFENSE] / 3) + 2 * (self.head['baseStats'][constants.SPECIAL_DEFENSE] / 3))
        #self.stats[constants.SPEED] = math.floor((2 * (self.body['baseStats'][constants.SPEED] / 3) )+ (self.head['baseStats'][constants.SPEED]/3))
        #self.type1 = self.head["types"][0]
        if len(self.body["types"]) == 1:
            if not (self.body["types"][0] is self.head["types"][0]):
                self.type2 = self.body["types"][0]
            else:
                self.type2 = "typeless" #Ho-Oh/Entei is fire type
        else:
            self.type2 = self.body["types"][1]
        
    def setHead(self,newHead):
        self.head = pokedex[newHead]

    def setBody(self,newBody):
        self.body = pokedex[newBody]

    def as_input(self): #if id not set, set with Cantor pairing function
        if (self.body is None or self.head is None):
            return 0
        if self.id == 0:
            self.id = 0.5 * (self.head["num"] + self.body["num"]) * (self.head["num"] + self.body["num"] + 1) + self.body["num"]
        return self.id
    
    def set_fusion(self,newId):
        self.id = newId
        w = math.floor(math.sqrt(self.id * 8 + 1) - 1 / 2) #w and t are intermediary values
        t = ((w + 1) * w) / 2
        body_num = self.id - t
        head_num = w - body_num
        for pokemon in pokedex:
            if pokemon["num"] == body_num:
                self.body = pokemon
            if pokemon["num"] == head_num:
                self.head = pokemon
            if not (self.body is None or self.head is None) and self.head["num"] == head_num and self.body["num"] == body_num:
                break

        
    
        
    
        
