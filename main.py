from infer import predict
from sensor import read_acc
from infer import convert
from screen import display, off
from aws_configs import AWS_CONFIGS

import numpy as np
import torch
import time
import RPi.GPIO as GPIO
from awscrt import mqtt, http
from awsiot import mqtt_connection_builder
import sys
import time
import json
import datetime

#AWS Configurations
input_endpoint = AWS_CONFIGS["endpoint"]
input_port = AWS_CONFIGS['port']
input_cert = AWS_CONFIGS['cert']
input_key = AWS_CONFIGS['key']
input_ca = AWS_CONFIGS['ca']
input_clientId = "0001"
input_topic = f"devices/{input_clientId}" 

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))

# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)

def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print("Resubscribe results: {}".format(resubscribe_results))

    for topic, qos in resubscribe_results['topics']:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))

# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    global received_count
    received_count += 1
    if received_count == input_count:
        received_all_event.set()

# Callback when the connection successfully connects
def on_connection_success(connection, callback_data):
    assert isinstance(callback_data, mqtt.OnConnectionSuccessData)
    print("Connection Successful with return code: {} session present: {}".format(callback_data.return_code, callback_data.session_present))

# Callback when a connection attempt fails
def on_connection_failure(connection, callback_data):
    assert isinstance(callback_data, mqtt.OnConnectionFailureData)
    print("Connection failed with error code: {}".format(callback_data.error))
    
# Callback when a connection has been disconnected or shutdown successfully
def on_connection_closed(connection, callback_data):
    print("Connection closed")

 # Create a MQTT connection from the command line data
mqtt_connection = mqtt_connection_builder.mtls_from_path(
  endpoint=input_endpoint,
  port=input_port,
  cert_filepath=input_cert,
  pri_key_filepath=input_key,
  ca_filepath=input_ca,
  on_connection_interrupted=on_connection_interrupted,
  on_connection_resumed=on_connection_resumed,
  client_id=input_clientId,
  clean_session=False,
  keep_alive_secs=30,
  on_connection_success=on_connection_success,
  on_connection_failure=on_connection_failure,
  on_connection_closed=on_connection_closed)

connect_future = mqtt_connection.connect()
connect_future.result()
print("Connected to AWS IoT Core")

print("Subscribing to topic '{}'...".format(input_topic))
subscribe_future, packet_id = mqtt_connection.subscribe(
    topic=input_topic,
    qos=mqtt.QoS.AT_LEAST_ONCE,
    )

subscribe_result = subscribe_future.result()
print("Subscribed with {}".format(str(subscribe_result['qos'])))

print("Starting system...")

#Data Labels
data_labels = {0.0:"Walk", 1.0: "WalkUp", 2.0: "WalkDw", 3.0: "Sit", 4.0: "Stand", 5.0: "Lay"}

##Button Pin Definition
button = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(button, GPIO.IN)

#Setting up data collection

while GPIO.input(button) != False:
    window = [[], [], []]
    window_size = 128
    
    while len(window[0]) < window_size:
        ax, ay, az = read_acc()
        window[0].append(ax)
        window[1].append(ay)
        window[2].append(az)
        time.sleep(0.02)

    window_converted = convert(window)
    prediction, con = predict(window_converted)
    datetime_now = datetime.datetime.now()

    display(str(data_labels[prediction]), str(round(con * 100, 2)))
    print(str(datetime_now), "\t", f"Prediction: {data_labels[prediction]}")

    #Uploading to AWS IoT Core
    
    message_string = {
        "ts": str(datetime_now),
        "p": str(data_labels[prediction]),
        "x": window[0],
        "y": window[1],
        "z": window[2]
        }
    message_json = json.dumps(message_string)
    mqtt_connection.publish(
        topic=input_topic,
        payload=message_json,
        qos=mqtt.QoS.AT_LEAST_ONCE)

disconnect_future = mqtt_connection.disconnect()
disconnect_future.result() 

print("Disconnected!") 
off()

