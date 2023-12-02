import tensorflow as tf
import keras.api._v2.keras as ks

class PlayerAgent():
    outputs = (4+5+1,) #4 moves, 5 switches, and forfeit
    inputs = (6*(2+1+1+1)+6*(2+1+1)+4+4,) #6 pokemon, 2 types, 1 item, 1 ability, current hp, 6 enemies with 2 types and ability and item, 4 opponent's moves, 4 of our moves
    def __init__(self,model_name : str = ''):
        if(model_name!=''):
            self.model = ks.models.load_model("models/" + model_name + ".keras")
        else:
            self.model = ks.Sequential()
            self.model.add(ks.layers.Dense(128, activation=tf.nn.relu, input_shape=PlayerAgent.inputs))
            self.model.add(ks.layers.Flatten())
            self.model.add(ks.layers.Dense(64, activation=tf.nn.relu))
            self.model.add(ks.layers.Dense(PlayerAgent.outputs, activation="linear"))
    
    def train(self):
        
        