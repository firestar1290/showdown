import constants
import math

from data import pokedex
    
class Fusion():
    def __init__(self):
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
    def updateStats(self):
        self.stats[constants.HITPOINTS] = math.floor((self.body['baseStats'][constants.HITPOINTS] / 3) + 2 * (self.head['baseStats'][constants.HITPOINTS] / 3))
        self.stats[constants.ATTACK] = math.floor((2 * (self.body['baseStats'][constants.ATTACK] / 3)) + (self.head['baseStats'][constants.ATTACK]/3))
        self.stats[constants.SPECIAL_ATTACK] = math.floor((self.body['baseStats'][constants.SPECIAL_ATTACK] / 3) + 2 * (self.head['baseStats'][constants.SPECIAL_ATTACK] / 3))
        self.stats[constants.DEFENSE] = math.floor((2 * (self.body['baseStats'][constants.DEFENSE] / 3)) + (self.head['baseStats'][constants.DEFENSE]/3))
        self.stats[constants.SPECIAL_DEFENSE] = math.floor((self.body['baseStats'][constants.SPECIAL_DEFENSE] / 3) + 2 * (self.head['baseStats'][constants.SPECIAL_DEFENSE] / 3))
        self.stats[constants.SPEED] = math.floor((2 * (self.body['baseStats'][constants.SPEED] / 3) )+ (self.head['baseStats'][constants.SPEED]/3))
    def updateStat(self,stat,newStat):
        self.stats[stat] = newStat
    def setHead(self,newHead):
        self.head = pokedex[newHead]
    def setBody(self,newBody):
        self.body = pokedex[newBody]
    
        
    
        
    
        
