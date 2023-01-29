#!/usr/bin/env python3

import asyncio
import random
from mavsdk import System
from mavsdk.geofence import Point
from mavsdk.action import OrbitYawBehavior
import datetime
from datetime import timedelta
import numpy as np
import os
import json

PORT = 14540
NUMDRONES = 1
NUMPOINTS = 2
STATUS = ['F','M'] 
EPSILON = 0.9
DISCOUNT_FACTOR = 0.9
LEARNING_RATE = 0.9

class Wildfire:
    
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

    async def land_all(status_text_task):
        for num in range(NUMDRONES):
            print("Drone "+str(num))
            drone = System()
            portDrone= num+PORT
            await drone.connect(system_address="udp://:"+str(portDrone))
            print("-- Landing")
            await drone.action.land()

            status_text_task.cancel()
            
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

            points = ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","Ñ","O","P","Q","R","S","T","U","V","W","X","Y","Z"]
            for num_point in range(NUMPOINTS):
                latitude_point = (num_point+1) * random.random() * 0.001 + Wildfire.latitude_origin
                longitude_point = (num_point+1) * random.random() * 0.001  + Wildfire.longitude_origin
                Wildfire.POINTS[points[num_point]] = Point(latitude_point, longitude_point)

        def update_status():
            for point in list(Wildfire.POINTS.keys()):
                for battery_level in range(2,11):
                    status = point + str(battery_level)
                    STATUS.append(status)
        
        def update_q_values():
            # Si existe el json con los qvalues lo carga
            if os.path.isfile("q_values.json"):
                with open("q_values.json") as json_file:
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
            else:
                if(status == "PC10"):
                    reward= -50
                else:
                    reward = diff * Wildfire.rewards[status] + Wildfire.rewards[status]
                Wildfire.points_time[point] = now
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
            print("Going to " + name_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + await get_status() + ")")
            
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

            if(actual_point == "PC"):
                if is_flying:      #Se optimiza para que cargue más rapido cuando esté en el suelo
                    print("Acting on point " + actual_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + actual_status + ")")
                    await drone.action.land()

                    i=0
                    async for in_air_local in drone.telemetry.in_air():
                        if(i%20==0):
                            print("Trying to land, still in air. Still " + str(round(await Wildfire.get_altitude(drone),2)) + " from ground.")
                        i = i+1
                        if not in_air_local:
                            is_flying=False
                            break
                print("Charging battery at " + actual_point + " with " + str(round(await Wildfire.get_battery(drone)*100,2)) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + await get_status() + ")")

            else:
                print("Monitoring point " + actual_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + actual_status + ")")
                await drone.action.do_orbit(radius_m=2.0, velocity_ms=10.0, yaw_behavior = OrbitYawBehavior.HOLD_FRONT_TO_CIRCLE_CENTER, latitude_deg = Wildfire.POINTS[actual_point].latitude_deg, longitude_deg = Wildfire.POINTS[actual_point].longitude_deg, absolute_altitude_m = Wildfire.absolute_altitude_origin + 20)
                await asyncio.sleep(10)

            #Wildfire.record[idDrone].append(actual_point)     solo se añade cuando hace go_to
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

        while(status != "M"):
            
            status = await get_status()

            action_index=get_next_action(status, EPSILON)

            #perform the chosen action, and transition to the next state (i.e., move to the next location)
            old_status = status #store the old row and column indexes

            status = await get_next_status(action_index, idDrone)

            #receive the reward for moving to the new state, and calculate the temporal difference
            reward = Wildfire.get_updated_rewards(idDrone, status)

            old_q_value = Wildfire.q_values[old_status][action_index]
            temporal_difference = reward + (DISCOUNT_FACTOR * np.max(Wildfire.q_values[status])) - old_q_value
            
            new_q_value = old_q_value + (LEARNING_RATE * temporal_difference)
            Wildfire.q_values[old_status][action_index] = new_q_value #actualización
            with open("q_values.json", 'w') as outfile:
                json.dump(Wildfire.q_values, outfile, indent=1) #actualización en json

        await reset_episode(drone, episode)

    
    async def run():
        print("Drone 0")
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
            Wildfire.flying_alt = Wildfire.absolute_altitude_origin + 40
            break

        Wildfire.update_constants()
        Wildfire.record.append([])
        Wildfire.last_action.append([])
        for episode in range(20):
            Wildfire.update_points_time()
            Wildfire.record[0].append("PC")
            print("-- Arming")
            await drone.action.arm()
            
            print("-- Taking off")
            await drone.action.takeoff()
            await Wildfire.AIDrone(0,drone,episode)    # 0 es idDrone

        print("Training completed")


async def print_status_text(drone):
    try:
        async for status_text in drone.telemetry.status_text():
            print(f"Status: {status_text.type}: {status_text.text}")
    except asyncio.CancelledError:
        return

async def get_drones():
    list_drones = []
    for num in range(NUMDRONES):
        drone= System()
        portDrone= num+PORT
        await drone.connect(system_address="udp://:"+str(portDrone))
        list_drones.append(drone)
    return list_drones

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    #loop.run_until_complete(Wildfire.calculate_coordinates())
    loop.run_until_complete(Wildfire.run())