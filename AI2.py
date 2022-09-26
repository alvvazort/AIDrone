#Importamos las librerias necesarias para el ejemplo
import gym
import random
import numpy as np
from keras.models     import Sequential
from keras.layers     import Dense
from keras.optimizers import Adam

env = gym.make('CartPole-v1') #creamos nuestro entorno de trabajo
env.reset()
goal_steps = 500  # definimos el número de pasos para el entrenamiento
score_requirement = 60 #puntuación requerida
intial_games = 10000  #Entrenanmiento inicial

#Función que ejecuta un bucle para hacer varias acciones para jugar el 
#juego.Por eso, intentar jugaremos hasta 500 pasos como máximo.
def play_a_random_game_first():
    try:
        for step_index in range(goal_steps):
            #env.render() #PAra representar el juego
            action = env.action_space.sample() #Elegimos acción al azar
            #Acción aleatoria a través de la función que elige los 
            #los resultado del siguiente paso, según la acción pasada como
            #parametro
            #[ObsType, float, bool, bool, dict]
            observation, reward, truncated, done, info = env.step(action)
            print("Paso {}:".format(step_index))
            print("Acción: {}".format(action))
            print("Observacion: {}".format(observation))
            print("Recompensa: {}".format(reward))
            print("Done: {}".format(done))
            print("Info: {}".format(info))
            if done:#Si juego completado
                break
    finally:
        env.reset()

play_a_random_game_first()

def model_data_preparation():
    training_data = []  # inicializamos los arrays con los datos de
    accepted_scores = [] #entrenamiento y las puntuaciones
    #Jugamos 10000 veces para obtener unos datos representativos
    for game_index in range(intial_games):
        score = 0 #inicializamos variables
        game_memory = []
        previous_observation = []
        #inidicamos que se ejeccute 500 veces
        for step_index in range(goal_steps):
            action = random.randrange(0, 2)#Acción aleatoria.Iz=0 y De=1
            observation, reward, truncated, done, info = env.step(action)
            #almacenamos puntuacion
            if len(previous_observation) > 0:
                game_memory.append([previous_observation, action])
                
            previous_observation = observation
            score += reward
            if done:
                break
            
        if score >= score_requirement:
            accepted_scores.append(score)
            for data in game_memory:
                if data[1] == 1:
                    output = [0, 1]
                elif data[1] == 0:
                    output = [1, 0]
                training_data.append([data[0], output])
        
        #resteamos entorno y lo mostramos por pantalla
        env.reset()

    print(accepted_scores)
    
    return training_data

training_data = model_data_preparation()