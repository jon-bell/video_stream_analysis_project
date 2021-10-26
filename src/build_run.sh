#!/bin/bash
# Saving build/ run commands so I don't forget
docker build -f dockerfile.opencv -t pipeline .
docker run -p 5000:5000 pipeline

# This command gets the IP address of a docker container
#docker network inspect -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}' <container_id>