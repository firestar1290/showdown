from showdown.battle import Battle
import cnn
import fusion

from ..helpers import format_decision

class BattleBot(Battle):
    def __init__(self, *args, **kwargs):
        super(BattleBot, self).__init__(*args, **kwargs)

    def find_best_move(self) -> list[str]: #returns a list, but only reads list[0], see run_battle.py line 38
        agent = cnn.PlayerAgent()
