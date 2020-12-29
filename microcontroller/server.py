import asyncio
import os
import re
from microcontroller_comm import MicrocontrollerComm

# Server config
START = 'start'
STOP = 'stop'
BRIGHTNESS = 'brightness'
ANGLE = 'angle'

enabled = int(os.environ['SERIAL_ENABLED'])

if enabled:
    controller = MicrocontrollerComm(port=os.environ['SERIAL_DEVICE'],
                                     baudrate=int(os.environ['SERIAL_BAUD']))


async def handle_command(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    supported_endpoints = [START, STOP, BRIGHTNESS, ANGLE]
    re_result = re.match('^(?P<message>({}|{}|{}|{}))(?P<param> \d+)?'.format(*supported_endpoints), message)

    async def send_response(message):
        writer.write(message.encode())
        await writer.drain()
        writer.close()

    if re_result is None or re_result.group('message') is None:
        print('Did not find endpoint in the URL.')
        await send_response('error')
        return
    
    addr = writer.get_extra_info('peername')
    message = re_result.group('message')

    if message == START:
        controller.infrared_running = True
        await send_response('ok')
        return

    if message == STOP:
        controller.infrared_running = False
        await send_response('ok')
        return

    if message == BRIGHTNESS:
        await send_response(f'{controller.brightness}')
        return

    if message == ANGLE:
        angle = re_result.group('param')
        if angle is None:
            await send_response('error')
            return
        controller.set_servo_angle(int(angle))
        await send_response('ok')
        return
        
    print(f'{addr} hit unrecognized endpoint.')
    await send_response('error')

async def wait_for_commands(addr, port):
    server = await asyncio.start_server(
        handle_command,
        addr,
        port
    )
    print(f"Listening on {addr}:{port}")
    async with server:
        await server.serve_forever()

async def main():
    """
    Starts a socket server and serial comms.
    """
    await asyncio.gather(
        wait_for_commands('0.0.0.0', int(os.environ['MC_SERVER_PORT'])),
        controller.loop()
    )

if enabled:
    asyncio.run(main())
else:
    print('Serial/microcontroller support is disabled. Aborting')
