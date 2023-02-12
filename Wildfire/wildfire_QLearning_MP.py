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
STATUS = ['F','M'] 
EPSILON = 0.9
DISCOUNT_FACTOR = 0.9
LEARNING_RATE = 0.9

class Wildfire:

    def setup_logger(name, log_file, level=logging.INFO):
        """To setup as many loggers as you want"""
        if(not os.path.exists("LOGS")):
            os.mkdir("LOGS")
        if os.path.isfile(log_file):
            created_at=open(log_file).readline().rstrip().split(",")[0].replace(" ","_")
            shutil.copy(log_file, "LOGS/"+name+"_"+str(NUMPOINTS)+"P_"+created_at+".log")
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
    is_flying = False
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
    
    log_point_matrix = setup_logger('point_matrix', "LOGS/points_matrix_"+str(NUMPOINTS)+"P.log")
    log_actions_states = setup_logger('actions_states', "LOGS/actions_states_"+str(NUMPOINTS)+"P.log")
    log_rewards = setup_logger('rewards', "LOGS/rewards_"+str(NUMPOINTS)+"P.log")
    

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
            for point in list(Wildfire.POINTS.keys()):
                for battery_level in range(2,11):
                    status = point + str(battery_level)
                    STATUS.append(status)
        
        def update_q_values():
            # Si existe el json con los qvalues lo carga
            if os.path.isfile("JSON/q_values_"+str(NUMPOINTS)+"P.json"):
                with open("JSON/q_values_"+str(NUMPOINTS)+"P.json") as json_file:
                    Wildfire.q_values = json.load(json_file)
            else:
                for status in STATUS:
                    Wildfire.q_values[status]=list(np.zeros(NUMPOINTS+2)) # Un cero por cada go_to a cada punto + 1 por act + 1 por PC

        def update_rewards():
            
            for status in STATUS:
                if status == "M":
                    Wildfire.rewards[status]= -5000
                elif "PC" in status or status == "F":
                    Wildfire.rewards[status]= 0
                else:
                    Wildfire.rewards[status]= 20
                    
        def update_actions(): 
            Wildfire.actions_functions.append("act")
            for point in list(Wildfire.POINTS.keys()):
                Wildfire.actions_functions.append("go_to_" + point)
  
        update_points()
        update_status()
        update_q_values()
        update_rewards()
        update_actions()
        
    def update_points_time():
            for point in list(Wildfire.POINTS.keys()):
                Wildfire.points_time[point]= datetime.datetime.now().strftime('%H:%M:%S')

    def pretty_print_dicc_raster():
        dimension = math.ceil(math.sqrt(NUMPOINTS*3))
        matrix_razer = np.empty((dimension, dimension), dtype="<U10")
        try:
            drone_point = Wildfire.record[0][-1]        #TODO CAMBIAR 0 POR IDDRONE FUTURO
        except:
            pass
        for k,v in Wildfire.dicc_raster.items():
            state=""
            if "Hueco" in k:
                state="🌳"
            else:
                state=k
            if v[2]:
                state="🔥"
            try: 
                if drone_point == k:
                    state = "🚁"
            except:
                pass
            matrix_razer[v[0]][v[1]]=state
        Wildfire.log_point_matrix.info("\n" + str(matrix_razer))
        print(matrix_razer)

    def get_updated_rewards(idDrone, status):
        if status == "M":
            return -5000
        elif status == "F":
            return 0
        else: #Calcular recompensa en función del tiempo pasado si se vigila un punto
            point = Wildfire.record[idDrone][-1]
            now = datetime.datetime.now().strftime('%H:%M:%S')
            monitorized_time = Wildfire.points_time[point]
            fecha_now = datetime.datetime.strptime(now, '%H:%M:%S')
            fecha_monitorized_time = datetime.datetime.strptime(monitorized_time, '%H:%M:%S')
            
            diff = (fecha_now - fecha_monitorized_time)/ timedelta(minutes=1) 

            if Wildfire.last_action[idDrone] == "go_to":
                if Wildfire.record[idDrone][-1] == Wildfire.record[idDrone][-2]:
                    return -20
                else:
                    reward = Wildfire.rewards[status]
                Wildfire.count_actions = 0
            else:
                Wildfire.count_actions+=1
                if(status == "PC10"):
                    reward= -50
                else: 
                    fire_reward = 0
                    if Wildfire.dicc_raster[point][2]:
                        fire_reward = 20 / (1 + Wildfire.count_actions/5)
                    
                    reward = diff * Wildfire.rewards[status] + Wildfire.rewards[status] + fire_reward
                Wildfire.points_time[point] = now
                Wildfire.log_rewards.info(Wildfire.last_action[idDrone]+" "+ Wildfire.record[idDrone][-1] + " " + str(round(reward,2)))
            return reward

    async def AIDrone(idDrone,drone, episode):

        async def go_to(idDrone, point):

            global is_flying
            if not is_flying:
                print("-- Arming")
                await drone.action.arm()
                print("-- Taking off")
                await drone.action.takeoff()
                
            await drone.action.goto_location(point.latitude_deg, point.longitude_deg, Wildfire.flying_alt, 0)
            is_flying=True

            battery = round(await Wildfire.get_battery(drone)*100,2)    
            name_point = [k for k, v in Wildfire.POINTS.items() if v == point][0]
            text_log="Going to " + name_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + await get_status() + ")"
            print(text_log)
            Wildfire.log_actions_states.info(text_log)
            async for position in drone.telemetry.position():
                #Comprueba que llega al punto    
                if abs(position.latitude_deg-point.latitude_deg)<0.00001 and abs(position.longitude_deg-point.longitude_deg)<0.00001: 
                    Wildfire.record[idDrone].append(name_point) # Guarda en el historial en que punto está
                    Wildfire.last_action[idDrone] = "go_to"
                    break
        
        async def act(idDrone):
            actual_point = Wildfire.record[idDrone][-1]
            battery = round(await Wildfire.get_battery(drone)*100,2)
            actual_status = await get_status()    
            global is_flying

            if not (actual_status == "M" or actual_status == "F"):
                if(actual_point == "PC"):
                    if is_flying:      #Se optimiza para que cargue más rapido cuando esté en el suelo
                        text_log = "Acting on point " + actual_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + actual_status + ")"
                        print(text_log)
                        Wildfire.log_actions_states.info(text_log)
                        await drone.action.land()

                        i=0
                        async for in_air_local in drone.telemetry.in_air():
                            if(i%20==0):
                                text_log = "Trying to land, still in air. Still " + str(round(await Wildfire.get_altitude(drone),2)) + " from ground."
                                print(text_log)
                                Wildfire.log_actions_states.info("Trying to land, still in air. Still " + str(round(await Wildfire.get_altitude(drone),2)) + " from ground.")
                            i = i+1
                            if not in_air_local:
                                is_flying=False
                                break
                    text_log = "Charging battery at " + actual_point + " with " + str(round(await Wildfire.get_battery(drone)*100,2)) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + await get_status() + ")"
                    print(text_log)
                    Wildfire.log_actions_states.info(text_log)

                else:
                    text_log = "Monitoring point " + actual_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + actual_status + ")"
                    print(text_log)
                    Wildfire.log_actions_states.info(text_log)
                    
                    await drone.action.do_orbit(radius_m=2.0, velocity_ms=10.0, yaw_behavior = OrbitYawBehavior.HOLD_FRONT_TO_CIRCLE_CENTER, latitude_deg = Wildfire.POINTS[actual_point].latitude_deg, longitude_deg = Wildfire.POINTS[actual_point].longitude_deg, absolute_altitude_m = Wildfire.absolute_altitude_origin + 40)
                    await asyncio.sleep(10)

                Wildfire.last_action[idDrone] = "act"
            
        async def get_battery_status(drone):
            battery= await Wildfire.get_battery(drone)
            #battery_levels = {1 : 0.16, 2: 0.45, 3: 0.60, 4: 0.8, 5: 1.0}
            battery_levels = {1 : 0.16, 2: 0.25, 3: 0.35, 4: 0.45, 5:0.55 , 6: 0.65, 7: 0.75, 8: 0.85, 9: 0.95 , 10: 1.0}
            battery_status = [k for k, v in battery_levels.items() if v >= battery][0]
            return battery_status

        async def get_status():
            battery_status = await get_battery_status(drone)
            point = Wildfire.record[idDrone][-1]
            global is_flying

            if(battery_status==1):
                if(point=="M"):
                    return "F"
                if is_flying:
                    Wildfire.record[idDrone].append("M")
                    print("Mayday! Mayday! Drone without battery " + "(M)")

                    return "M"
            
            status = point+str(battery_status)
            return status

        def get_next_action(state, epsilon):
            #if a randomly chosen value between 0 and 1 is less than epsilon, 
            #then choose the most promising value from the Q-table for this state.
            if np.random.random() < epsilon:
                return np.argmax(Wildfire.q_values[state])
            else: #choose a random action
                return np.random.randint(NUMPOINTS+2) # Un posibilidad por cada go_to a cada punto + 1 por act + 1 por PC
        
        async def get_next_status(action_index, idDrone):
            action=Wildfire.actions_functions[action_index]
            if(action=="act"):
                await act(idDrone)
            else: 
                point_string= action.split("_")[-1]
                point = Wildfire.POINTS[point_string]
                await go_to(idDrone, point)
            return await get_status()

        async def reset_episode(drone, episode):
            await drone.action.goto_location(Wildfire.POINTS["PC"].latitude_deg, Wildfire.POINTS["PC"].longitude_deg, Wildfire.flying_alt, 0)
            async for position in drone.telemetry.position():
                #Comprueba que llega al punto    
                if abs(position.latitude_deg-Wildfire.POINTS["PC"].latitude_deg)<0.00001 and abs(position.longitude_deg-Wildfire.POINTS["PC"].longitude_deg)<0.00001: 
                    break
            
            # Aterriza y carga la batería
            global is_flying
            if is_flying:      
                    await drone.action.land()
                    async for in_air_local in drone.telemetry.in_air():
                        if not in_air_local:
                            is_flying=False
                            break
                        
            await asyncio.sleep(4)
            print("Starting new episode - Episode " + str(episode+1))

        
        global is_flying
        is_flying = True

        status = await get_status()

        while not (status == "M" or status == "F"):
            
            #status = await get_status()

            action_index=get_next_action(status, EPSILON)

            #perform the chosen action, and transition to the next state (i.e., move to the next location)
            old_status = status #store the old row and column indexes

            status = await get_next_status(action_index, idDrone)

            #receive the reward for moving to the new state, and calculate the temporal difference
            reward = Wildfire.get_updated_rewards(idDrone, status)
            print("Reward: " + str(round(reward,2)))
            Wildfire.total_reward += reward
                
            old_q_value = Wildfire.q_values[old_status][action_index]

            temporal_difference = reward + (DISCOUNT_FACTOR * np.max(Wildfire.q_values[status])) - old_q_value
            
            new_q_value = old_q_value + (LEARNING_RATE * temporal_difference)
            Wildfire.q_values[old_status][action_index] = new_q_value #actualización

            with open("JSON/q_values_"+str(NUMPOINTS)+"P.json", 'w') as outfile:
                json.dump(Wildfire.q_values, outfile, indent=1) #actualización en json
        
        print("Map reset, wildfire was extinguished")
        for k,v in Wildfire.dicc_raster.items():
            Wildfire.dicc_raster[k] = (Wildfire.dicc_raster[k][0], Wildfire.dicc_raster[k][1], False)
        
        print("Accumulated reward: " + str(round(Wildfire.total_reward,2)))
        await reset_episode(drone, episode)
        Wildfire.log_rewards.info("Accumulated reward of episode " + str(episode) + ": " + str(round(Wildfire.total_reward,2)))
        Wildfire.total_reward = 0.
            
    async def run_fire():
        await asyncio.sleep(10)
        fire.start_dicc_fire_time(Wildfire.dicc_raster)
        while(True):    
            fire_points = [(k,v) for k, v in Wildfire.dicc_raster.items() if v[2] == True]
            if (fire_points == []):          # Si no hay fuego, lo inicia 
                Wildfire.dicc_raster= fire.start_fire(Wildfire.dicc_raster)
            Wildfire.dicc_raster=fire.fire_propagation(Wildfire.dicc_raster)
            Wildfire.pretty_print_dicc_raster()
            await asyncio.sleep(60)

    async def run():
        Wildfire.log_rewards.info("Action Point Reward")

        print("Drone 0 ready to start routine")
        drone = System()
        await drone.connect(system_address="udp://:"+str(PORT))

        #status_text_task = asyncio.ensure_future(print_status_text(drone))

        print("Waiting for drone to have a global position estimate...")
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("-- Global position estimate OK")
                break

        print("Fetching home location coordinates and altitude...")
        async for terrain_info in drone.telemetry.home():
            Wildfire.latitude_origin = terrain_info.latitude_deg
            Wildfire.longitude_origin = terrain_info.longitude_deg
            Wildfire.absolute_altitude_origin = terrain_info.absolute_altitude_m
            Wildfire.flying_alt = Wildfire.absolute_altitude_origin + 60
            break

        Wildfire.update_constants()
        print("The " + str(NUMPOINTS) + " points of the problem have been rasterized as: ")
        Wildfire.pretty_print_dicc_raster()
        Wildfire.record.append([])
        Wildfire.last_action.append([])
        for episode in range(20):
            Wildfire.update_points_time()
            Wildfire.record[0].append("PC")
            print("-- Arming")
            await drone.action.arm()
            
            print("-- Taking off")
            await drone.action.takeoff()
            #loop = asyncio.get_event_loop()
            #asyncio.ensure_future(Wildfire.run_fire())
            #asyncio.ensure_future(Wildfire.AIDrone(0,drone,episode))
            await Wildfire.AIDrone(0,drone,episode)    # 0 es idDrone
            #loop.run_forever()

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
    
