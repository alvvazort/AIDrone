#!/usr/bin/env python3

import asyncio
from mavsdk import System
from mavsdk.geofence import Point, Polygon
import datetime

PORT = 14540
NUMDRONES = 1
STATUS = ['F','M','A2','A3','A4','A5','PC2', 'PC3', 'PC4', 'PC5'] 


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
    #TODO Hacer que se guarden los estados y no los puntos, mirar la bateria del dron
    async def go_to(point, idDron):
        await drone.action.goto_location(point.latitude_deg, point.longitude_deg, flying_alt, 0)
        async for position in drone.telemetry.position():
            if abs(position.latitude_deg-point.latitude_deg)<0.000001 and abs(position.longitude_deg-point.longitude_deg)<0.000001:
                name_point = [k for k, v in POINTS.items() if v == point][0]
                record[idDron].append(name_point)
                print("Point " + name_point + " arrived at " + str(datetime.datetime.now()))
                break
            
    async def act(idDron):

        actual_point = record[idDron][-1]
        if(actual_point == "PC"):
            await drone.action.land()
        else:
            await asyncio.sleep(10)
            print("Acting on point " + actual_point + " at " + str(datetime.datetime.now()))

        record[idDron].append(actual_point)

    def AIDrone(idDron):
        
        if(record[idDron][-1]== "PC"):
            pass
        else:
            pass

        
    for idDron in range(NUMDRONES):
        record.append(["PC"])
        print("Drone "+str(idDron))
        drone = System()
        portDrone= idDron+PORT
        await drone.connect(system_address="udp://:"+str(portDrone))

        status_text_task = asyncio.ensure_future(print_status_text(drone))

        print("Waiting for drone to have a global position estimate...")
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("-- Global position estimate OK")
                break
        if(idDron==0):
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

        AIDrone()
        
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