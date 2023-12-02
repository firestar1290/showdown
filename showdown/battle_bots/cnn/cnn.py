import tensorflow as tf
import keras.api._v2.keras as ks

class PlayerAgent():
    outputs = (4+5+1,) #4 moves, 5 switches, and forfeit
    inputs = (6*(4+1+1+1+1+4)+1+6*(4+1+1+1+1+4)+1+1,) #6 pokemon each (4 moves types, 1 ability, 1 item, 1 non-volatile status, 1 current hp, 4 moves), 1 currently active for player 1, 1 currently active for player 2, 1 turn number
    def __init__(self,model_name : str = ''):
        if(model_name!=''):
            self.model = ks.models.load_model("models/" + model_name + ".keras")
        else:
            self.model = ks.Sequential()
            self.model.add(ks.layers.Dense(128, activation=tf.nn.relu, input_shape=PlayerAgent.inputs))
            self.model.add(ks.layers.Flatten())
            self.model.add(ks.layers.Dense(64, activation=tf.nn.relu))
            self.model.add(ks.layers.Dense(PlayerAgent.outputs, activation="linear"))
    
    def train(self,model_name = ''):
        pass
        
if __name__ == "__main__":
    agent = PlayerAgent()
    agent.train("showdown/battle_bots/cnn/models/main_model.keras")