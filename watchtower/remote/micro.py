import asyncio
import logging
import os
import time

async def open_connection():
    return await asyncio.open_connection(
        os.environ['MC_SERVER_HOST'],
        int(os.environ['MC_SERVER_PORT'])
    )

last_brightness_request = 0
brightness_reading = "-1"

def get_brightness():
    global brightness_reading
    global last_brightness_request

    async def __get_brightness():
        global brightness_reading
        global last_brightness_request
        logging.getLogger(__name__).debug('Requesting new brightness.')
        last_brightness_request = time.time()
        reader, writer = await open_connection()
        writer.write('brightness'.encode())
        data = await reader.read(100)
        writer.close()
        brightness_reading = data.decode()

    # Request the brightness a max of every second.
    if time.time() - last_brightness_request > 1:
        asyncio.run(__get_brightness())
    return brightness_reading

def set_running(running: bool):
    if not int(os.environ['SERIAL_ENABLED']):
        return

    async def __set_running():
        reader, writer = await open_connection()
        if running:
            writer.write('start'.encode())
        else:
            writer.write('stop'.encode())
        data = await reader.read(100)
        writer.close()
        if not data.decode() == 'ok':
            logging.getLogger(__name__).error('Failed to start/stop microcontroller.')
    asyncio.run(__set_running())

def set_angle(angle: int):
    async def __set_angle():
        reader, writer = await open_connection()
        writer.write(f'angle {angle}'.encode())
        data = await reader.read(100)
        writer.close()
        if not data.decode() == 'ok':
            logging.getLogger(__name__).error('Error setting servo angle.')
    asyncio.run(__set_angle())
    