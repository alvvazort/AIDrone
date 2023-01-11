#!/usr/bin/env python3

import asyncio
from mavsdk import System
from mavsdk.geofence import Point, Polygon

PORT = 14540
NUMDRONES = 1
ESTADOS = ['F','M','A2','A3','A4','A5','PC2', 'PC3', 'PC4', 'PC5'] 


async def run():
    
    latitude = 0
    longitude = 0
    absolute_altitude = 0
    flying_alt = 80

    PC = Point(latitude - 0.001, longitude - 0.001)
    A = Point(latitude + 0.001, longitude - 0.001)

    async def land_all(status_text_task):
        for num in range(NUMDRONES):
            print("Drone "+str(num))
            drone = System()
            portDrone= num+PORT
            await drone.connect(system_address="udp://:"+str(portDrone))
            print("-- Landing")
            await drone.action.land()

            status_text_task.cancel()

    async def go_to(point):
        await drone.action.goto_location(point.latitude_deg, point.longitude_deg, flying_alt, 0)

    for num in range(NUMDRONES):
        print("Drone "+str(num))
        drone = System()
        portDrone= num+PORT
        await drone.connect(system_address="udp://:"+str(portDrone))

        status_text_task = asyncio.ensure_future(print_status_text(drone))


        print("Waiting for drone to have a global position estimate...")
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("-- Global position estimate OK")
                break
        if(num==0):
            # Fetch the home location coordinates, in order to set a boundary around the home location
            print("Fetching home location coordinates and altitude...")
            async for terrain_info in drone.telemetry.home():
                latitude = terrain_info.latitude_deg
                longitude = terrain_info.longitude_deg
                absolute_altitude = terrain_info.absolute_altitude_m
                flying_alt = absolute_altitude + 40
                PC = Point(latitude - 0.001, longitude - 0.001)
                A = Point(latitude + 0.001, longitude - 0.001)
                break
        

        print("-- Arming")
        await drone.action.arm()
        
        print("-- Taking off")
        await drone.action.takeoff()

        await asyncio.sleep(2)

        await go_to(PC)
        async for position in drone.telemetry.position():
            if abs(position.latitude_deg-PC.latitude_deg)<0.000001 and abs(position.longitude_deg-PC.longitude_deg)<0.000001:
                print("Point arrived")
                break
        await go_to(A)


        #drone.__del__()


    await asyncio.sleep(2)


    



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