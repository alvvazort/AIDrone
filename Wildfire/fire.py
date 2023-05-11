import numpy as np
import math
import asyncio
import datetime as datetime
from datetime import timedelta


wildfire = False
wildfire_probability = 0.1
wildfire_propagation = 0.1
wildfire_extinguished = 0.1
dicc_fire_time = {}

def start_dicc_fire_time(dicc_raster):
    for k in dicc_raster.keys():
        dicc_fire_time[k] = datetime.datetime.now()

def start_fire(dicc_raster):
    fire_prob = np.random.random()
    if(fire_prob < wildfire_probability):
        key = list(dicc_raster)[np.random.randint(0,len(dicc_raster))]
        origin_fire = dicc_raster[key]
        origin_fire = (origin_fire[0], origin_fire[1], True)
        global wildfire
        wildfire = True
        dicc_raster[key]= origin_fire
        dicc_fire_time[key] = datetime.datetime.now()
        
    return dicc_raster

def get_adjacent(dicc_raster, fire_point):
    fire_points = [(k,v) for k, v in dicc_raster.items() if abs(v[0] - fire_point[0]) + abs(v[1] - fire_point[1]) == 1]   #Solo adyacentes
    return fire_points 

def fire_propagation(dicc_raster):

    fire_points = [(k,v) for k, v in dicc_raster.items() if v[2] == True]

    for fire_point in fire_points:
        points_adjacents = get_adjacent(dicc_raster, fire_point[1])
        for adjacent in points_adjacents:
            if(np.random.random()<wildfire_propagation and adjacent[1][2] == False):        #Solo se propaga a los no incendiados
                k = adjacent[0]
                v = adjacent[1]
                
                val = (v[0],v[1], True)
                dicc_raster[k]=val
                dicc_fire_time[k] = datetime.datetime.now()
        
        wildfire_extinguished_time = wildfire_extinguished + ((datetime.datetime.now() - dicc_fire_time[fire_point[0]])/timedelta(minutes=1))*0.005
        if(np.random.random() < wildfire_extinguished_time):
            dicc_raster[fire_point[0]] = (dicc_raster[fire_point[0]][0], dicc_raster[fire_point[0]][1], False)  
    return dicc_raster


