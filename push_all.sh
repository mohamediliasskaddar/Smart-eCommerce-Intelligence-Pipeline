#!/bin/bash

USERNAME="mohamediliasskaddar"

echo "Login Docker..."
docker login

echo "Tagging images..."
docker tag smart-ecommerce-intelligence-dashboard:latest $USERNAME/e-commerce-dashboard:latest
docker tag smart-ecommerce-intelligence-pipeline:latest $USERNAME/e-commerce-pipeline:latest
docker tag smart-ecommerce-intelligence-agents:latest $USERNAME/e-commerce-agents:latest

echo "Pushing images..."
docker push $USERNAME/e-commerce-dashboard:latest
docker push $USERNAME/e-commerce-pipeline:latest
docker push $USERNAME/e-commerce-agents:latest

echo "Done"