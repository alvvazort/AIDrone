#!/usr/bin/env python3

import asyncio
from mavsdk import System


async def run():

    numDrones=3
    port= 14540

    
    for num in range(numDrones):
        print("Drone "+str(num))
        drone = System()
        portDrone= num+port
        await drone.connect(system_address="udp://:"+str(portDrone))

        status_text_task = asyncio.ensure_future(print_status_text(drone))


        print("Waiting for drone to have a global position estimate...")
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("-- Global position estimate OK")
                break

        print("-- Arming")
        await drone.action.arm()

        print("-- Taking off")
        await drone.action.takeoff()

        drone.__del__()


    await asyncio.sleep(2)


    for num in range(numDrones):
        print("Drone "+str(num))
        drone = System()
        portDrone= num+port
        await drone.connect(system_address="udp://:"+str(portDrone))
        print("-- Landing")
        await drone.action.land()

        status_text_task.cancel()



async def print_status_text(drone):
    try:
        async for status_text in drone.telemetry.status_text():
            print(f"Status: {status_text.type}: {status_text.text}")
    except asyncio.CancelledError:
        return

async def get_drones(port,numDrones):
    list_drones = []
    for num in range(numDrones):
        drone= System()
        portDrone= num+port
        await drone.connect(system_address="udp://:"+str(portDrone))
        list_drones.append(drone)
    return list_drones

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())