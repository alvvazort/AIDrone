#!/usr/bin/env python3

import asyncio
from mavsdk import System
from mavsdk.geofence import Point
from mavsdk.action import OrbitYawBehavior
import datetime
import value_and_policy_iteration

PORT = 14540
NUMDRONES = 1
STATUS = ['F','M','A2','A3','A4','A5','PC2', 'PC3', 'PC4', 'PC5'] 
POLICY_METHOD = "value iteration"

async def run():
    
    latitude = 0
    longitude = 0
    absolute_altitude = 0
    flying_alt = 80
    record = []

    PC = Point(latitude, longitude)
    A = Point(latitude + 0.001, longitude - 0.001)
    POINTS= {}
    
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
        async for in_air in drone.telemetry.in_air():
            print(f"In air: {in_air}")
            break


    async def print_position(drone):
        async for position in drone.telemetry.position():
            print(position)
            break
            
    async def AIDrone(idDrone):
        
        async def go_to(idDrone):
            last_point = record[idDrone][-1]
            #TODO Cuando haya más puntos habría que cambiarlo
            if(last_point=="PC"): #Si está en un punto, va hacia el otro punto 
                point= POINTS["A"]
            else:
                point= POINTS["PC"]

            await drone.action.goto_location(point.latitude_deg, point.longitude_deg, flying_alt, 0)
            battery = round(await get_battery(drone)*100,2)    
            name_point = [k for k, v in POINTS.items() if v == point][0]
            print("Going to " + name_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + await get_status() + ")")
            
            async for position in drone.telemetry.position():
                #Comprueba que llega al punto    
                if abs(position.latitude_deg-point.latitude_deg)<0.000001 and abs(position.longitude_deg-point.longitude_deg)<0.000001: 
                    record[idDrone].append(name_point) # Guarda en el historial en que punto está
                    break
        
        async def act(idDrone):
            actual_point = record[idDrone][-1]
            battery = round(await get_battery(drone)*100,2)    

            #TODO Mirar como se carga la bateria cuando este en suelo
            if(actual_point == "PC"):
                print("Acting on point " + actual_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + await get_status() + ")")
                await drone.action.land()

                i=0
                async for in_air in drone.telemetry.in_air():
                    
                    if(i%3==0):
                        print(f"Trying to land, still in air: {in_air}")
                    i = i+1
                    break
            elif(actual_point == "M"):
                print("Mayday! Mayday! Drone without battery " + "(" + await get_status() + ")")
            else:

                await drone.action.do_orbit(radius_m=2.0, velocity_ms=10.0, yaw_behavior = OrbitYawBehavior.HOLD_FRONT_TO_CIRCLE_CENTER, latitude_deg = POINTS[actual_point].latitude_deg, longitude_deg = POINTS[actual_point].longitude_deg, absolute_altitude_m = absolute_altitude + 20)
                print("Acting on point " + actual_point + " with " + str(battery) + " percentage at " + str(datetime.datetime.now().strftime('%H:%M:%S')) + " (" + await get_status() + ")")
                await asyncio.sleep(10)

            record[idDrone].append(actual_point)
            
        async def get_battery_status(drone):
            battery= await get_battery(drone)
            battery_levels = {1 : 0.20, 2: 0.40, 3: 0.60, 4: 0.80, 5: 1.0}
            
            battery_status = [k for k, v in battery_levels.items() if v >= battery][0]
            return battery_status

        #['F','M','A2','A3','A4','A5','PC2', 'PC3', 'PC4', 'PC5'] 
        async def get_status():
            battery_status = await get_battery_status(drone)
            point = record[idDrone][-1]
            
            if(battery_status==1):
                if(record[idDrone][-1]=="M"):
                    return "F"
                record[idDrone].append("M")
                return "M"
            
            status = point+str(battery_status)
            return status
            
        policy = value_and_policy_iteration.wildfire_one_charge_one_point(POLICY_METHOD)
        actions_functions = [act,go_to]
        actions = ["Actua", "Viaja"]
        
        status = await get_status()
        while(status != "M"):
            status = await get_status()
            action=actions_functions[policy[STATUS.index(status)]]

            await action(idDrone)

        
    for idDrone in range(NUMDRONES):
        record.append(["PC"])
        print("Drone "+str(idDrone))
        drone = System()
        portDrone= idDrone+PORT
        await drone.connect(system_address="udp://:"+str(portDrone))

        status_text_task = asyncio.ensure_future(print_status_text(drone))

        print("Waiting for drone to have a global position estimate...")
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("-- Global position estimate OK")
                break
        if(idDrone==0):
            # Fetch the home location coordinates, in order to set a boundary around the home location
            print("Fetching home location coordinates and altitude...")
            async for terrain_info in drone.telemetry.home():
                latitude = terrain_info.latitude_deg
                longitude = terrain_info.longitude_deg
                absolute_altitude = terrain_info.absolute_altitude_m
                flying_alt = absolute_altitude + 40
                PC = Point(latitude, longitude)
                A = Point(latitude + 0.001, longitude - 0.001)
                POINTS= {
                    "PC": PC,
                    "A": A
                }
                break
        
        print("-- Arming")
        await drone.action.arm()
        
        
        print("-- Taking off")
        await drone.action.takeoff()
        
        await AIDrone(idDrone)

        #drone.__del__()


    await asyncio.sleep(2)

    await land_all(status_text_task)


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
    loop.run_until_complete(run())