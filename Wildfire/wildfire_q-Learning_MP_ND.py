#!/usr/bin/env python3

import asyncio
import math
import random
import shutil
from mavsdk import System
from mavsdk.geofence import Point
from mavsdk.action import OrbitYawBehavior
import datetime
from datetime import timedelta
import numpy as np
import os
import json
import fire
import logging

PORT = 14540
NUMPOINTS = 5
NUMDRONES = 2 
STATUS = [] 
EPSILON = 0.9
DISCOUNT_FACTOR = 0.9
LEARNING_RATE = 0.9
NUM_EPOCHS = 20

class Wildfire:

    def setup_logger(name, log_file, level=logging.INFO):
        """To setup as many loggers as you want"""
        if(not os.path.exists("LOGS")):
            os.mkdir("LOGS")
        if os.path.isfile(log_file):
            created_at=open(log_file).readline().rstrip().split(",")[0].replace(" ","_")
            shutil.copy(log_file, "LOGS/"+name+"_"+str(NUMPOINTS)+"P_"+str(NUMDRONES)+"D_"+created_at+".log")
            os.remove(log_file)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

        handler = logging.FileHandler(log_file)        
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        logger.info("Creation of log "+name)

        return logger
    
    latitude_origin = 0
    longitude_origin = 0
    absolute_altitude_origin = 0
    flying_alt = 80
    is_flying = []
    record = []
    PC = Point(latitude_origin, longitude_origin)
    POINTS = {}
    points_time = {}
    q_values = {}
    actions_functions = []
    rewards = {}
    last_action = []
    dicc_raster = {}
    count_actions= 0
    total_reward = 0.
    drones=[]
    all_final_status = []
    
    log_point_matrix = setup_logger('point_matrix', "LOGS/points_matrix_"+str(NUMPOINTS)+"P_"+str(NUMDRONES)+"D.log")
    log_actions_states = setup_logger('actions_states', "LOGS/actions_states_"+str(NUMPOINTS)+"P_"+str(NUMDRONES)+"D.log")
    log_rewards = setup_logger('rewards', "LOGS/rewards_"+str(NUMPOINTS)+"P_"+str(NUMDRONES)+"D.log")
    
    async def print_battery(drone):
        async for battery in drone.telemetry.battery():
            print(f"{battery.remaining_percent}")
            break
    
    async def get_battery(drone):
        async for battery in drone.telemetry.battery():
            return battery.remaining_percent

    async def print_gps_info(drone):
        async for gps_info in drone.telemetry.gps_info():
            print(f"GPS info: {gps_info}")
            break

    async def print_in_air(drone):
        async for in_air_local in drone.telemetry.in_air():
            print(f"In air: {in_air_local}")
            break

    async def print_position(drone):
        async for position in drone.telemetry.position():
            print(position)
            break
    
    async def get_altitude(drone):
        async for position in drone.telemetry.position():
            return position.relative_altitude_m
    
    def combine(terms,res_list, accum=''):
        last = (len(terms) == 1)
        n = len(terms[0])
        for i in range(n):
            if accum != '':
                item = accum + "-" + terms[0][i] 
            else:
                item = terms[0][i] 
            if last:
                res_list.append(item)
            else:
                Wildfire.combine(terms[1:], res_list, item)   

    def update_constants():    

        def update_points():
            
            PC = Point(Wildfire.latitude_origin, Wildfire.longitude_origin)
            Wildfire.POINTS["PC"] = PC
            coordenadas = {}
            coordenadas["PC"] = [Wildfire.latitude_origin, Wildfire.longitude_origin]
            
            points = ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","Ñ","O","P","Q","R","S","T","U","V","W","X","Y","Z"]
            
            dimension = math.ceil(math.sqrt(NUMPOINTS*3))
            #matrix_raster=[]
            index_points=0
            for fila in range(dimension):
                for columna in range(dimension):
                    fire = False
                    if(((columna+fila*dimension)%3==0 and fila%2==0) or ((columna+fila*dimension)%3==2 and fila%2!=0)) and index_points<NUMPOINTS:      #Esto permite que los puntos aparezcan mas esparcidos en el mapa raster 
                        Wildfire.dicc_raster[points[index_points]]=(fila,columna,fire)
                        #matrix_raster[fila,columna] = (points[index_points],fire)
                        index_points+=1
                    else:
                        Wildfire.dicc_raster["Hueco"+str(columna+fila*dimension)]=(fila,columna,fire)
                        #matrix_raster[fila,columna] = ("Hueco",fire)
            
            for num_point in range(NUMPOINTS):
                coordenada_raster_lat = Wildfire.dicc_raster[points[num_point]][0] 
                latitude_point =  (Wildfire.latitude_origin - 0.0001) - (coordenada_raster_lat * 0.0005)/3     
                
                coordenada_raster_lon = Wildfire.dicc_raster[points[num_point]][1] 
                longitude_point =  (Wildfire.longitude_origin - 0.001) + (coordenada_raster_lon * 0.0005)/3           
                Wildfire.POINTS[points[num_point]] = Point(latitude_point, longitude_point)
                coordenadas[points[num_point]] = [latitude_point, longitude_point]
                    
        def update_status(): 

            estados = ["M","F"]
            for point in list(Wildfire.POINTS.keys()):
                for battery_level in range(2,11):
                    estados.append(point + str(battery_level))
            
            all_estados = []
            for idDrone in range(NUMDRONES):
                all_estados.append(estados)

            Wildfire.combine(all_estados, STATUS)

        def update_q_values():
            # Si existe el json con los qvalues lo carga
            if os.path.isfile("JSON/q_values_"+str(NUMPOINTS)+"P_" + str(NUMDRONES) +"D.json"):
                with open("JSON/q_values_"+str(NUMPOINTS)+"P_" + str(NUMDRONES) +"D.json") as json_file:
                    Wildfire.q_values = json.load(json_file)
            else:
                num_acciones = int(math.pow(NUMPOINTS+2,NUMDRONES))     # goto a num points + act + go_to pc
                for status in STATUS:
                    Wildfire.q_values[status]=list(np.zeros(num_acciones))

        def update_rewards():
            estados = ["M","F"]
            for point in list(Wildfire.POINTS.keys()):
                for battery_level in range(2,11):
                    estados.append(point + str(battery_level))
            for status in estados:
                if status == "M":
                    Wildfire.rewards[status]= -5000
                elif "PC" in status or status == "F":
                    Wildfire.rewards[status]= 0
                else:
                    Wildfire.rewards[status]= 20
                    
        def update_actions():   
            actions_drone=[]
            actions_drone.append("act")
            for point in list(Wildfire.POINTS.keys()):
                actions_drone.append("go_to_" + point)
            
            acciones = []
            for idDrone in range(NUMDRONES):
                acciones.append(actions_drone)
            Wildfire.combine(acciones,Wildfire.actions_functions)
  
        update_points()
        update_status()
        update_q_values() 
        update_rewards()
        update_actions()
        
    def update_points_time():   #Inicializar los puntos con el tiempo de cada epoca
            for point in list(Wildfire.POINTS.keys()):
                Wildfire.points_time[point]= datetime.datetime.now().strftime('%H:%M:%S')

    def pretty_print_dicc_raster():          
        dimension = math.ceil(math.sqrt(NUMPOINTS*3))
        matrix_razer = np.empty((dimension, dimension), dtype="<U10")
        drone_points = []
        for idDrone in range(NUMDRONES):
            try:
                drone_points.append(Wildfire.record[idDrone][-1])      
            except:
                pass
        for k,v in Wildfire.dicc_raster.items():
            state=""
            if v[2] == True:
                if "Hueco" in k :
                    state="🔥🍂"
                else: # Punto de vigilancia
                    state=k+"🔥"
                    for drone_point in drone_points: 
                        if drone_point == k:
                            state = k +"🚒"
            else: # No hay fuego
                if "Hueco" in k :
                    state="🌳🌿"
                else: # Punto de vigilancia
                    state=k+"🌿"
                    for drone_point in drone_points: 
                        if drone_point == k:
                            state = k +"🚁"

            matrix_razer[v[0]][v[1]]=state
        Wildfire.log_point_matrix.info("\n" + str(matrix_razer))
        print(matrix_razer)

    def get_updated_rewards(status):
        
        # Formato status: "EstadoDrone1-EstadoDrone2-..."
        status_splitted = status.split("-")
        total_reward=0
        for idDrone, drone_status in enumerate(status_splitted):
            same_action = False
            for i in range(idDrone+1,NUMDRONES):  # Recorremos la lista record viendo el ultimo punto de cada dron, si coincide y además hacen la misma accion
                if(Wildfire.record[idDrone][-1] == Wildfire.record[i][-1] and Wildfire.last_action[idDrone] == Wildfire.last_action[i]):  # No se le recompensa
                    same_action= True 

            if drone_status == "M":
                total_reward+= -5000
            elif drone_status == "F":
                total_reward+= 0
            else:
                if not same_action: # Si hay varios drones actuando en el mismo punto, solo se recompensa a uno
                    point = Wildfire.record[idDrone][-1]
                    now = datetime.datetime.now().strftime('%H:%M:%S')
                    monitorized_time = Wildfire.points_time[point]
                    fecha_now = datetime.datetime.strptime(now, '%H:%M:%S')
                    fecha_monitorized_time = datetime.datetime.strptime(monitorized_time, '%H:%M:%S')
                    diff = (fecha_now - fecha_monitorized_time)/ timedelta(minutes=1)   #Calcular recompensa en función del tiempo pasado si se vigila un punto   

                    if Wildfire.last_action[idDrone] == "go_to":
                        if Wildfire.record[idDrone][-1] == Wildfire.record[idDrone][-2]:
                            total_reward += -20
                        else:
                            total_reward += Wildfire.rewards[drone_status]
                        Wildfire.count_actions = 0
                    else:
                        if point != "PC":
                            Wildfire.count_actions+=1
                            fire_reward = 0
                            if Wildfire.dicc_raster[point][2]:
                                fire_reward = 20 / (1 + Wildfire.count_actions/5)
                            
                            total_reward += diff * Wildfire.rewards[drone_status] + Wildfire.rewards[drone_status] + fire_reward
                            Wildfire.points_time[point] = now
        
        log_last_actions = ""
        log_points = ""
        for i in range(NUMDRONES):
            log_last_actions += str(Wildfire.last_action[i]) + "-"
            log_points += str(Wildfire.record[i][-1]) + "-"
            if i == NUMDRONES-1:
                log_last_actions[:-1]
                log_points[:-1]
        Wildfire.log_rewards.info(log_last_actions + " " + log_points + " " + str(round(total_reward,2)))
        return total_reward

    async def AIDrone(episode):

        async def go_to(idDrone, point, multiple_status):        
            drone = Wildfire.drones[idDrone]
            actual_status = multiple_status.split("-")[idDrone]

            if not Wildfire.is_flying[idDrone]:
                print("-- Arming")
                await drone.action.arm()
                print("-- Taking off")
                await drone.action.takeoff()
                
            await drone.action.goto_location(point.latitude_deg, point.longitude_deg, Wildfire.flying_alt + idDrone, 0)
            Wildfire.is_flying[idDrone]=True

            battery = round(await Wildfire.get_battery(drone)*100,2)    
            name_point = [k for k, v in Wildfire.POINTS.items() if v == point][0]
            text_log="Drone "+str(idDrone)+" going to " + name_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + actual_status + ")"
            print(text_log)
            Wildfire.log_actions_states.info(text_log)
            async for position in drone.telemetry.position():
                #Comprueba que llega al punto    
                if abs(position.latitude_deg-point.latitude_deg)<0.00001 and abs(position.longitude_deg-point.longitude_deg)<0.00001: 
                    Wildfire.record[idDrone].append(name_point) # Guarda en el historial en que punto está
                    Wildfire.last_action[idDrone] = "go_to"
                    break
        
        async def act(idDrone, multiple_status):
            drone = Wildfire.drones[idDrone]
            actual_point = Wildfire.record[idDrone][-1]
            battery = round(await Wildfire.get_battery(drone)*100,2)
            actual_status = multiple_status.split("-")[idDrone]

            if not (actual_status == "M" or actual_status == "F"):
                if(actual_point == "PC"):
                    if Wildfire.is_flying[idDrone]:      #Se optimiza para que cargue más rapido cuando esté en el suelo
                        text_log = "Drone "+str(idDrone)+" acting on point " + actual_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + actual_status + ")"
                        print(text_log)
                        Wildfire.log_actions_states.info(text_log)
                        await drone.action.land()

                        i=0
                        async for in_air_local in drone.telemetry.in_air():
                            if(i%20==0):
                                text_log = "Drone "+str(idDrone)+" trying to land, still in air. Still " + str(round(await Wildfire.get_altitude(drone),2)) + " from ground."
                                print(text_log)
                                Wildfire.log_actions_states.info("Drone "+str(idDrone)+" trying to land, still in air. Still " + str(round(await Wildfire.get_altitude(drone),2)) + " from ground.")
                            i = i+1
                            if not in_air_local:
                                Wildfire.is_flying[idDrone]=False
                                break
                    text_log = "Drone "+str(idDrone)+" charging battery at " + actual_point + " with " + str(round(await Wildfire.get_battery(drone)*100,2)) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + actual_status + ")"
                    print(text_log)
                    Wildfire.log_actions_states.info(text_log)

                else:
                    text_log = "Drone "+str(idDrone)+" monitoring point " + actual_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + actual_status + ")"
                    print(text_log)
                    Wildfire.log_actions_states.info(text_log)
                    
                    await drone.action.do_orbit(radius_m=2.0, velocity_ms=10.0, yaw_behavior = OrbitYawBehavior.HOLD_FRONT_TO_CIRCLE_CENTER, latitude_deg = Wildfire.POINTS[actual_point].latitude_deg, longitude_deg = Wildfire.POINTS[actual_point].longitude_deg, absolute_altitude_m = Wildfire.absolute_altitude_origin + 20 + idDrone)
                    await asyncio.sleep(10)

                Wildfire.last_action[idDrone] = "act"
            
        async def get_battery_status(drone):
            battery= await Wildfire.get_battery(drone)
            #battery_levels = {1 : 0.16, 2: 0.45, 3: 0.60, 4: 0.8, 5: 1.0}
            battery_levels = {1 : 0.16, 2: 0.25, 3: 0.35, 4: 0.45, 5:0.55 , 6: 0.65, 7: 0.75, 8: 0.85, 9: 0.95 , 10: 1.0}
            battery_status = [k for k, v in battery_levels.items() if v >= battery][0]
            return battery_status

        async def get_status():  # Formato de estado: Punto Batería (x cada drone)
            status = ""
            for idDrone, drone in enumerate(Wildfire.drones):  
                battery_status = await get_battery_status(drone)
                point = Wildfire.record[idDrone][-1]
                if(battery_status==1):
                    if(point=="M"):
                        status+= "F-"
                    elif Wildfire.is_flying[idDrone]:
                        Wildfire.record[idDrone].append("M")
                        text_log = "Mayday! Mayday! Drone without battery " + "(M)"
                        Wildfire.log_actions_states.info(text_log)
                        print(text_log)
                        status+= "M-"
                    else:
                        status+= "F-"
                else:
                    status += point+str(battery_status)+"-"
            return status[:-1] # Elimina el último guión

        def get_next_action(state, epsilon):
            #if a randomly chosen value between 0 and 1 is less than epsilon, 
            #then choose the most promising value from the Q-table for this state.
            if np.random.random() < epsilon:
                return np.argmax(Wildfire.q_values[state])
            else: #choose a random action
                return np.random.randint(len(Wildfire.actions_functions)) # Un posibilidad por cada go_to a cada punto + 1 por act + 1 por PC
        
        async def get_next_status(action_index):
            async def do_action(action, idDrone,multiple_status):
                if(action=="act"):
                    await act(idDrone, multiple_status)
                else: 
                    point_string= action.split("_")[-1]
                    point = Wildfire.POINTS[point_string]
                    await go_to(idDrone, point, multiple_status)

            actions=Wildfire.actions_functions[action_index] # Devuelve texto que descifra la accion Ex: act,go_to_B
            # Split por comas para cada acción
            actions_list=actions.split("-")
            do_action_list=[]
            multiple_status= await get_status() 
            status_splitted=multiple_status.split("-")
            for idDrone, action in enumerate(actions_list):
                if not (status_splitted[idDrone]=="M" or status_splitted[idDrone]=="F"):
                    do_action_list.append(do_action(action, idDrone, multiple_status))
            await asyncio.gather(*do_action_list)
            return await get_status() # Cuando todos hayan realizado la acción se calcula el estado

        async def reset_episode(episode):

            async def go_home_func(drone,idDrone):
                await drone.action.goto_location(Wildfire.POINTS["PC"].latitude_deg+idDrone/10000, Wildfire.POINTS["PC"].longitude_deg, Wildfire.flying_alt, 0)
                async for position in drone.telemetry.position():
                    #Comprueba que llega al punto    
                    if abs(position.latitude_deg-(Wildfire.POINTS["PC"].latitude_deg+idDrone/10000))<0.00001 and abs(position.longitude_deg-Wildfire.POINTS["PC"].longitude_deg)<0.00001: 
                        break

                if Wildfire.is_flying[idDrone]:  
                    await drone.action.land()
                    async for in_air_local in drone.telemetry.in_air():
                        if not in_air_local:
                            Wildfire.is_flying[idDrone]=False
                            break
                
            
            # Aterriza y carga la batería
            go_home = []
            
            for idDrone,drone in enumerate(Wildfire.drones):
                go_home.append(go_home_func(drone,idDrone))
            await asyncio.gather(*go_home)

            await asyncio.sleep(4)
            text_log = "Starting new episode - Episode " + str(episode+1)
            Wildfire.log_actions_states.critical(text_log)
            Wildfire.log_point_matrix.critical(text_log)
            Wildfire.log_rewards.critical(text_log)
            print(text_log)
            Wildfire.record = []
            for idDrone in NUMDRONES:
                Wildfire.record.append(["PC"])
                
        for idDrone in range(NUMDRONES):
            Wildfire.is_flying.append(True)
        
        status = await get_status()
        
        final_status = ["M","F"]
        multiple_final_status = []
        for idDrone in range(NUMDRONES):
            multiple_final_status.append(final_status)
        Wildfire.combine(multiple_final_status, Wildfire.all_final_status)
        
        while not (status in Wildfire.all_final_status): # Cada episodio se termina cuando todos los drones mueren
            
            action_index=get_next_action(status, EPSILON)  
            
            # perform the chosen action, and transition to the next state (i.e., move to the next location)
            old_status = status # store the old row and column indexes

            status = await get_next_status(action_index)     # Esperar al que tarde más y a partir de ahí seguir con la ejecución del codigo
               
            #receive the reward for moving to the new state, and calculate the temporal difference
            reward = Wildfire.get_updated_rewards(status)
            print("Reward: " + str(round(reward,2)))
            Wildfire.total_reward += reward
                
            old_q_value = Wildfire.q_values[old_status][action_index]

            temporal_difference = reward + (DISCOUNT_FACTOR * np.max(Wildfire.q_values[status])) - old_q_value
            
            new_q_value = old_q_value + (LEARNING_RATE * temporal_difference)
            Wildfire.q_values[old_status][action_index] = new_q_value #actualización

            with open("JSON/q_values_"+str(NUMPOINTS)+"P_" + str(NUMDRONES) +"D.json", 'w') as outfile:
                json.dump(Wildfire.q_values, outfile, indent=1) #actualización en json
        
        print("Map reset, wildfire was extinguished")
        for k,v in Wildfire.dicc_raster.items():
            Wildfire.dicc_raster[k] = (Wildfire.dicc_raster[k][0], Wildfire.dicc_raster[k][1], False)
        
        await reset_episode(episode)

        print("Accumulated reward: " + str(round(Wildfire.total_reward,2)))
        Wildfire.log_rewards.info("Accumulated reward of episode " + str(episode) + ": " + str(round(Wildfire.total_reward,2)))
        Wildfire.total_reward = 0.
            
    async def run_fire():
        await asyncio.sleep(60)
        fire.start_dicc_fire_time(Wildfire.dicc_raster)
        while(True):    
            fire_points = [(k,v) for k, v in Wildfire.dicc_raster.items() if v[2] == True]
            if (fire_points == []):          # Si no hay fuego, lo inicia 
                Wildfire.dicc_raster= fire.start_fire(Wildfire.dicc_raster)
            Wildfire.dicc_raster=fire.fire_propagation(Wildfire.dicc_raster)
            Wildfire.pretty_print_dicc_raster()
            await asyncio.sleep(60)
    
    async def connect_drone(idDrone):
        print("Drone " + str(idDrone) + " ready to start routine")
        Wildfire.record[idDrone].append("PC")
        portSys = 50050 + idDrone
        drone = System(mavsdk_server_address="127.0.0.1", port=portSys)
        
        await drone.connect()
        Wildfire.drones.append(drone)
        return drone

    async def global_position(drone):
        print("Waiting for drone to have a global position estimate...")
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("-- Global position estimate OK")
                break

    async def terrain_info(drone):
        print("Fetching home location coordinates and altitude...")
        async for terrain_info in drone.telemetry.home():
            Wildfire.latitude_origin = terrain_info.latitude_deg
            Wildfire.longitude_origin = terrain_info.longitude_deg
            Wildfire.absolute_altitude_origin = terrain_info.absolute_altitude_m
            Wildfire.flying_alt = Wildfire.absolute_altitude_origin + 60
            break

    async def start_drone(idDrone):
        await Wildfire.connect_drone(idDrone)
        await Wildfire.global_position(Wildfire.drones[idDrone])
        await Wildfire.terrain_info(Wildfire.drones[idDrone])

    async def run():
        def start_servers():
            absolute_path = os.path.dirname(__file__)
            print(absolute_path)
            relative_path = "start_servers.sh"
            full_path = os.path.join(absolute_path, relative_path)
            os.popen('sh '+ full_path + " " + str(NUMDRONES))

        start_servers()
        await asyncio.sleep(5)
        Wildfire.log_rewards.info("Action Point Reward")

        drone_starts=[]
        for idDrone in range(NUMDRONES): 
            Wildfire.record.append([])   
            Wildfire.last_action.append([])   
            drone_starts.append(Wildfire.start_drone(idDrone))
            
        await asyncio.gather(*drone_starts) #An asterisk * denotes iterable unpacking. Its operand must be an iterable. The iterable is expanded into a sequence of items.

        Wildfire.update_constants()
        print("The " + str(NUMPOINTS) + " points of the problem have been rasterized as: ")
        Wildfire.pretty_print_dicc_raster()
        
        for episode in range(NUM_EPOCHS): 
            Wildfire.update_points_time()
            arm_list=[]
            for idDrone,drone in enumerate(Wildfire.drones):
                arm_list.append(drone.action.arm())
                print("-- Arming Drone " + str(idDrone))
            await asyncio.gather(*arm_list)

            takeoff_list=[]            
            for idDrone,drone in enumerate(Wildfire.drones):
                takeoff_list.append(drone.action.takeoff())
                print("-- Taking off Drone " + str(idDrone))
            await asyncio.gather(*takeoff_list)
                
            await Wildfire.AIDrone(episode)    

        print("Training completed")

async def print_status_text(drone):
    try:
        async for status_text in drone.telemetry.status_text():
            print(f"Status: {status_text.type}: {status_text.text}")
    except asyncio.CancelledError:
        return

if __name__ == "__main__":
    main_loop = asyncio.get_event_loop()
    #loop.run_until_complete(Wildfire.calculate_coordinates())
    #main_loop.run_until_complete(Wildfire.run())        
    asyncio.ensure_future(Wildfire.run())
    asyncio.ensure_future(Wildfire.run_fire())
    main_loop.run_forever()
    
