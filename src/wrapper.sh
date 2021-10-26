#!/bin/bash

python3 streamgear_test.py &

sleep 2

python3 flask_server.py

