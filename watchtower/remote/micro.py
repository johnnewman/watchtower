import asyncio
import os

async def open_connection():
    return await asyncio.open_connection(
        os.environ['MC_SERVER_HOST'],
        int(os.environ['MC_SERVER_PORT'])
    )

async def get_brightness():
    reader, writer = await open_connection()
    writer.write('brightness'.encode())
    data = await reader.read(100)
    writer.close()
    return data.decode()

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
            print('Error reaching with microcontroller server.')
    asyncio.run(__set_running())

def set_angle(angle: int):
    async def __set_angle():
        reader, writer = await open_connection()
        writer.write(f'angle {angle}'.encode())
        data = await reader.read(100)
        writer.close()
        if not data.decode() == 'ok':
            print('Error setting servo angle.')
    asyncio.run(__set_angle())
    
    
    