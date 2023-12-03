import tensorflow as tf
import keras.api._v2.keras as ks
import csv
from os import listdir
from os.path import isfile, join

#labels = output, features = input
class PlayerAgent():
    outputs = 4+6+1 #4 moves, 6 switches, and forfeit
    inputs = (6*(4+1+1+1+1+4+6)+1+6*(4+1+1+1+1+4+6)+1+1,) #6 pokemon each (4 moves types, 1 ability, 1 item, 1 non-volatile status, 1 current hp, 4 moves, 6 base stats), 1 currently active for player 1, 1 currently active for player 2, 1 turn number
    def __init__(self,model_name : str = ''):
        if(model_name!=''):
            self.model = ks.models.load_model("models/" + model_name + ".keras")
        else:
            self.model = ks.Sequential()
            self.model.add(ks.layers.Normalization())
            self.model.add(ks.layers.Dense(128, activation=tf.nn.relu, input_shape=PlayerAgent.inputs))
            self.model.add(ks.layers.Flatten())
            self.model.add(ks.layers.Dense(64, activation=tf.nn.relu))
            self.model.add(ks.layers.Dense(PlayerAgent.outputs, activation="linear"))
    
    def train(self,model_name = ''):
        base_uri = "showdown/battle_bots/cnn/data/formatted_replays/train"
        outputs = [
            "forfeit",
            "move1",
            "move2",
            "move3",
            "move4",
            "switch1",
            "switch2",
            "switch3",
            "switch4",
            "switch5",
            "switch6"
        ]
        match_csv_dataset = tf.data.experimental.make_csv_dataset(
            base_uri + "/*.csv",
            batch_size=10, #arbitrary
            label_name="match",
            num_epochs=20, #arbitrary
            ignore_errors=True
        )
        for batch, label in match_csv_dataset.take(1):
            for key, value in batch.items():
              print(f"{key:20s}: {value}")
            print()
            print(f"{'label':20s}: {label}")

        
if __name__ == "__main__":
    agent = PlayerAgent()
    agent.train()