import asyncio
from openleadr import OpenADRServer, enable_default_logging
from openleadr.objects import Interval, Target
from openleadr.utils import generate_id
from functools import partial
from datetime import datetime, timedelta, timezone
import random

import aiohttp
from aiohttp import web
import json
from dict2obj import Dict2Obj
# from collections import defaultdict
# import weakref


enable_default_logging()


async def update_gui(msg):
    ws = server.app['websockets']; 
    await ws.send_str(json.dumps(msg)) 
    

async def on_create_party_registration(registration_info):
    if registration_info['ven_name'] == 'myVEN':
        registration_id = 'Registration001'
        ven_id = 'VEN001'
        data = {'ven_id': ven_id, 'ven_name': registration_info['ven_name']}
        msg = {'action': "register_ven", 'msg_id': generate_id(), 'data': data}
        await update_gui(msg)
        return ven_id, registration_id

async def on_register_report(ven_id, resource_id, measurement, unit, scale,
                       min_sampling_interval, max_sampling_interval):
    """
    Pick which reports we want to get.
    """
    print(measurement)
    if measurement == 'Status':
        callback = partial(receive_device_status, resource_id=resource_id)
        return callback, min_sampling_interval
    if measurement == 'Voltage':
        callback = partial(receive_metervalue, resource_id=resource_id, measurement=measurement)
        return callback, min_sampling_interval
    if measurement == 'RealPower':
        callback = partial(receive_metervalue, resource_id=resource_id, measurement=measurement)
        return callback, min_sampling_interval

RESOURCE_STATUS = {}
def receive_device_status(data, resource_id):
    for time, value in data:
        print(f"Storing {value} at {time}")

    RESOURCE_STATUS[resource_id] = value
    print(f"The status of the device is now {value}")

async def receive_metervalue(data, resource_id, measurement):
    """
    Receive reports as they come in from the VEN.
    """
    print(f"Got metervalue: {measurement} = {data}")
    for time, value in data:
        print(f"Storing {value}")
        

    print("Checking if we need to send an event")
    if measurement == 'Voltage':
        # Look up the current status of the device
        current_state = RESOURCE_STATUS.get(resource_id) or 0
        if current_state == 1 and value < 215:
            print("Yes, sending an event")
            # Turn the device off when the voltage is too low
            #signal_start = datetime.now(timezone.utc) + timedelta(seconds=5)
            signal_start = datetime.now() + timedelta(seconds=5)
            server.add_event(ven_id='VEN001',
                             signal_name='simple',
                             signal_type='level',
                             intervals=[Interval(dtstart=signal_start,
                                                 duration=timedelta(minutes=10),
                                                 signal_payload=0)],
                             target=[Target(resource_id='SmartInverter')],
                             callback=event_callback)

        elif current_state == 0 and value > 230:
            print("Yes, sending an event")
            #signal_start = datetime.now(timezone.utc) + timedelta(seconds=5)
            signal_start = datetime.now() + timedelta(seconds=5)
            server.add_event(ven_id='VEN001',
                             signal_name='simple',
                             signal_type='level',
                             intervals=[Interval(dtstart=signal_start,
                                                duration=timedelta(minutes=10),
                                                signal_payload=1)],
                             target=[Target(resource_id='SmartInverter')],
                             callback=event_callback)

def event_callback(opt_status):
    print(opt_status)





###############################################################################
#                                                                             #
#                              SERVER STARTUP                                 #
#                                                                             #
###############################################################################

# server = OpenADRServer(vtn_id='myvtn',
#                        requested_poll_freq=timedelta(seconds=5),
#                        http_host='0.0.0.0',
#                        http_cert='dummy_vtn.crt',
#                        http_key='dummy_vtn.key',
#                        http_ca_file='dummy_ca.crt',
#                        cert='dummy_vtn.crt',
#                        key='dummy_vtn.key')


server = OpenADRServer(vtn_id='myvtn',
                       requested_poll_freq=timedelta(seconds=5),
                       http_host='0.0.0.0')
server.add_handler('on_create_party_registration', on_create_party_registration)
server.add_handler('on_register_report', on_register_report)


async def gui(request):
    return web.FileResponse('./Demo VTN.html')

async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    request.app['websockets'] = ws

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                msg = json.loads(msg.data);    
                msg = Dict2Obj(msg)   
                data = {}         
                if(msg.action == "stop"):
                    data = {"action": "stopped_server"}
                if(msg.action == "start"):
                    data = {"action": "started_server"}  
                if(msg.action == "reply"):
                    if msg.data == "yes":
                        data = {"action": 'add_vens', "data": [{"ven_id": "VEN001", "ven_name": "myVEN"}]}  
                if(msg.action == "select_ven"):
                    data = {"action": "ven_info", "data": {"ven_id": "VEN001", "ven_name": "myVEN", "fingerprint": generate_id()}}  
                if(msg.action == 'create_event'):
                    signal_start = datetime.now() + timedelta(seconds=5)
                    server.add_event(ven_id = msg.data.ven_id, 
                                    signal_name = msg.data.signal_name, 
                                    signal_type = msg.data.signal_type,
                                    intervals=[Interval(dtstart=signal_start,
                                                        duration=timedelta(minutes=10),
                                                        signal_payload=1)],
                                    target=[Target(resource_id='SmartInverter')],
                                    callback=event_callback)
                    data = {"action": 'event_added',
                            "data": {
                                    "ven_id": "VEN001",
                                    "ven_name": "myVEN", 
                                    "signal_name": msg.data.signal_name,
                                    "signal_type": msg.data.signal_type,
                                    "signal_start": signal_start
                                    }
                            }
                              
                if(data):
                    await ws.send_str(json.dumps(data))

        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    print('websocket connection closed')

    return ws

server.app.add_routes([web.get('/', gui)])
server.app.add_routes([web.get('/ws', websocket_handler)])
# server.app['websockets'] = defaultdict(set)
#server.app['websockets'] = weakref.WeakSet()
server.app['websockets'] = {}
loop = asyncio.get_event_loop()
loop.create_task(server.run_async())
loop.run_forever()