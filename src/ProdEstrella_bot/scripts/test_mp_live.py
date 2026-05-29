"""
Test script: Verify MercadoPago integration is working in production.
Run this directly on the VPS inside the Docker container or as:
  docker exec prodestrella-bot-app-1 python /app/scripts/test_mp_live.py
"""
import asyncio
import os
import sys

# Load vars from .env if running outside docker
try:
    from dotenv import load_dotenv
    load_dotenv("/opt/prodEstrella_bot/.env")
except ImportError:
    pass

import mercadopago

access_token = os.environ.get("MP_ACCESS_TOKEN", "")
if not access_token:
    print("ERROR: MP_ACCESS_TOKEN not set!")
    sys.exit(1)

print(f"Testing with token: {access_token[:20]}...{access_token[-6:]}")

sdk = mercadopago.SDK(access_token)

preference_data = {
    "items": [
        {
            "title": "TEST - Lapiz Negro punta redonda",
            "unit_price": 1500.0,
            "quantity": 1,
            "currency_id": "ARS",
        }
    ],
    "payer": {"email": "test_buyer@test.com"},
    "external_reference": "test-order-001",
}

print("Creating preference...")
response = sdk.preference().create(preference_data)

print(f"Status: {response['status']}")
if response["status"] in (200, 201):
    print(f"SUCCESS! Init point URL: {response['response']['init_point']}")
    print(f"Preference ID: {response['response']['id']}")
else:
    print(f"ERROR: {response['response']}")
