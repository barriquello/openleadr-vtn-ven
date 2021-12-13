import asyncio
from openleadr import OpenADRServer, enable_default_logging
from openleadr.objects import Interval, Target
from openleadr.utils import generate_id
from functools import partial
from datetime import datetime, timedelta, timezone
import random

enable_default_logging()

def on_create_party_registration(registration_info):
    if registration_info['ven_name'] == 'myVEN':
        registration_id = 'Registration001'
        ven_id = 'VEN001'
        return ven_id, registration_id

def on_register_report(ven_id, resource_id, measurement, unit, scale,
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
        print(f"Storing {value}")

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
loop = asyncio.get_event_loop()
loop.create_task(server.run_async())
loop.run_forever()