from openleadr import OpenADRClient, enable_default_logging
import asyncio
from datetime import datetime, timezone, timedelta
from argparse import ArgumentParser
import random

parser = ArgumentParser()
parser.add_argument('offset', type=int, nargs='?')
args = parser.parse_args()

if args.offset:
    OFFSET = args.offset
else:
    OFFSET = 220

enable_default_logging()


RAND_V = OFFSET

STATUS = 0
def get_status():
    global STATUS
    return STATUS

async def change_status(status, delay):
    """
    Change the switch position after 'delay' seconds.
    """
    global STATUS
    if delay > 0:
        await asyncio.sleep(delay)
    if status == 1 and STATUS == 0:
        print("SWITCHING ON")
    elif status == 0 and STATUS == 1:
        print("SWITCHING OFF")
    STATUS = status

def read_voltage():
    """
    Read the power from the energy meter.
    """
    global STATUS
    global RAND_V
    
    if STATUS == 1: 
        RAND_V += random.choice([-1,0])
    else:
        RAND_V += random.choice([0,1])
    data = RAND_V    
    return data

def read_power():
    """
    Read the voltage value from the energy meter and return it
    """
    data = 100+random.choice([-1,0,1])
    return data

async def handle_event(event):
    """
    Do something based on the event.
    """

    loop = asyncio.get_event_loop()
    signal = event['event_signals'][0]
    intervals = signal['intervals']
    now = datetime.now(timezone.utc)
    for interval in intervals:
        start = interval['dtstart']
        delay = (start - now).total_seconds()
        value = interval['signal_payload']
        print(f"Setting status {value} after {delay} seconds.")
        loop.create_task(change_status(status=int(value),
                                       delay=delay))
    return 'optIn'

client = OpenADRClient(ven_name="myVEN",
                       vtn_url="http://localhost:8080/OpenADR2/Simple/2.0b")


client.add_report(resource_id='SmartInverter',
                  measurement='voltage',
                  sampling_rate=timedelta(seconds=5),
                  callback=read_voltage)

client.add_report(resource_id='SmartInverter',
                  measurement='real_power',
                  sampling_rate=timedelta(seconds=5),
                  callback=read_power)

client.add_report(resource_id='SmartInverter',
                  report_name='TELEMETRY_STATUS',
                  sampling_rate=timedelta(seconds=5),
                  callback=get_status)

client.add_handler('on_event', handle_event)

loop = asyncio.get_event_loop()
loop.create_task(client.run())
loop.run_forever()