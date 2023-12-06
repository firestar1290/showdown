from showdown.battle import Battle
import showdown.battle_bots.cnn.cnn as cnn
from showdown.battle import Fusion

from ..helpers import format_decision

class BattleBot(Battle):
    def __init__(self, *args, **kwargs):
        
        self.agent = cnn.PlayerAgent("main_model") #trained
        #self.agent = cnn.PlayerAgent() #untrained
        
        super(BattleBot, self).__init__(*args, **kwargs)

    def find_best_move(self): #returns a list, but only reads list[0], see run_battle.py line 38
        agent = cnn.PlayerAgent("main_model")
        inputs = []
        inputs += self.user.active.as_input().split(",")
        for pokemon_reserve in self.user.reserve:
            inputs += pokemon_reserve.as_input().split(',')
        inputs += [1]
        
        inputs += self.opponent.active.as_input().split(",")
        for pokemon_reserve in self.opponent.reserve:
            inputs += pokemon_reserve.as_input().split(',')
        inputs += [1]

        move_choice = agent.choose_move(inputs)
        
        if move_choice > 4:
            #switch
            if move_choice == 10:
                move = "switch " + self.user.reserve[-1].name
            else:
                move = "switch " + self.user.reserve[move_choice-5].name
        else:
            #use move
            move = self.user.active.moves[move_choice-1].name
        
        return format_decision(self,move)
