import numpy as np
import math
import asyncio


wildfire = False
wildfire_probability = 0.1
wildfire_propagation = 0.1
wildfire_extinguished = 0.1

NUMPOINTS = 5

def start_dicc_raster():
    dicc_raster={}

    points = ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","Ñ","O","P","Q","R","S","T","U","V","W","X","Y","Z"]
    
    dimension = math.ceil(math.sqrt(NUMPOINTS*3))
    index_points=0
    for fila in range(dimension):
        for columna in range(dimension):
            fire = False
            if(((columna+fila*dimension)%3==0 and fila%2==0) or ((columna+fila*dimension)%3==2 and fila%2!=0)) and index_points<NUMPOINTS:      #Esto permite que los puntos aparezcan mas esparcidos en el mapa raster 
                dicc_raster[points[index_points]]=(fila,columna,fire)
                index_points+=1
            else:
                dicc_raster["Hueco"+str(columna+fila*dimension)]=(fila,columna,fire)
            
    return dicc_raster

def start_fire(dicc_raster):
    fire_prob = np.random.random()
    if(fire_prob < wildfire_probability):
        key = list(dicc_raster)[np.random.randint(0,len(dicc_raster))]
        origin_fire = dicc_raster[key]
        origin_fire = (origin_fire[0], origin_fire[1], True)
        global wildfire
        wildfire = True
        dicc_raster[key]= origin_fire
        print("Wildfire started at " + str(key) + " (" + str(dicc_raster[key][0]) + ", " + str(dicc_raster[key][1]) + ")")

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
                print("Wildfire was propagated to point "+k+" ("+str(v[0])+", "+str(v[1])+")")
                
                val = (v[0],v[1], True)
                dicc_raster[k]=val
                
        if(np.random.random() < wildfire_extinguished):
            dicc_raster[fire_point[0]] = (dicc_raster[fire_point[0]][0], dicc_raster[fire_point[0]][1], False)  
            print("Wildfire was extinguished at point " + str(fire_point[0]))  
    return dicc_raster

async def propagation():
    global dicc_raster
    while(True):
        fire_points = [(k,v) for k, v in dicc_raster.items() if v[2] == True]
        if (fire_points == []):
            start_fire(dicc_raster)
        dicc_raster=fire_propagation(dicc_raster)
        await asyncio.sleep(10)

dicc_raster = start_dicc_raster()

while(wildfire == False):
    start_fire(dicc_raster)
    
loop = asyncio.get_event_loop()
loop.run_until_complete(propagation())

