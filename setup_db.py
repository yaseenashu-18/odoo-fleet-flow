from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/fleetflow')
client = MongoClient(MONGO_URI)
db = client.get_database()
bcrypt = Bcrypt()

def setup():
    # Clear existing data for demo purposes
    db.users.delete_many({})
    db.vehicles.delete_many({})
    db.trips.delete_many({})
    db.maintenance.delete_many({})

    # Create Authorized Admins
    admins = [
        {'email': 'burrarikshith@gmail.com', 'pass': 'Bikky@0027'},
        {'email': 'yaseenashu0108@gmail.com', 'pass': 'Ysn@1874'}
    ]
    
    for admin in admins:
        hashed_pass = bcrypt.generate_password_hash(admin['pass']).decode('utf-8')
        db.users.insert_one({
            'username': admin['email'], # Using email as username
            'password': hashed_pass,
            'role': 'Admin',
            'created_at': datetime.utcnow()
        })

    # Create Mock Vehicles
    vehicles = [
        {'plate': 'MH 01 AB 1234', 'model': 'Tata Prima 4028.S', 'type': 'Trailer Truck', 'capacity': '40 tons', 'odometer': 12500, 'status': 'Idle'},
        {'plate': 'MH 02 CD 5678', 'model': 'Ashok Leyland Dost', 'type': 'Mini Van', 'capacity': '2 tons', 'odometer': 8900, 'status': 'Active'},
        {'plate': 'MH 03 EF 9101', 'model': 'BharatBenz 3523R', 'type': 'Container', 'capacity': '25 tons', 'odometer': 45000, 'status': 'In Shop'},
    ]
    vehicle_ids = db.vehicles.insert_many(vehicles).inserted_ids

    # Create Mock Trips
    trips = [
        {
            'vehicle_id': str(vehicle_ids[1]), 
            'cargo_weight': 1500, 
            'driver': 'John Doe', 
            'origin': 'Mumbai Port', 
            'destination': 'Pune Warehouse', 
            'fuel_cost': 5000, 
            'status': 'On Trip', 
            'created_at': datetime.utcnow()
        }
    ]
    db.trips.insert_many(trips)

    # Create Mock Maintenance
    maintenance = [
        {
            'vehicle_id': str(vehicle_ids[2]), 
            'issue': 'Engine Overheating', 
            'date': '2025-02-20', 
            'cost': 15000, 
            'status': 'New', 
            'created_at': datetime.utcnow()
        }
    ]
    db.maintenance.insert_many(maintenance)

    # Create Mock Drivers
    drivers = [
        {'name': 'Manikanta', 'license': 'DL678910', 'license_expiry': '2027-12-31', 'completion_rate': 98, 'safety_score': 95, 'complaints': 0, 'status': 'On Duty'},
        {'name': 'Rikshith', 'license': 'DL112233', 'license_expiry': '2023-01-01', 'completion_rate': 85, 'safety_score': 70, 'complaints': 2, 'status': 'On Duty'}, # Expired
        {'name': 'Yaseen', 'license': 'DL445566', 'license_expiry': '2026-06-15', 'completion_rate': 100, 'safety_score': 99, 'complaints': 0, 'status': 'On Duty'},
    ]
    db.drivers.insert_many(drivers)

    # Create Mock Expenses
    expenses = [
        {'trip_id': '650000000001', 'driver': 'Manikanta', 'distance': 450, 'fuel_cost': 12000, 'misc_cost': 2500, 'liters': 80, 'status': 'Done', 'created_at': datetime.utcnow()},
        {'trip_id': '650000000002', 'driver': 'Yaseen', 'distance': 320, 'fuel_cost': 8500, 'misc_cost': 1200, 'liters': 55, 'status': 'Done', 'created_at': datetime.utcnow()},
    ]
    db.expenses.insert_many(expenses)

    print("Database setup complete with authorized admin data!")
    print("Authorized Admins:")
    print("1. burrarikshith@gmail.com / Bikky@0027")
    print("2. yaseenashu0108@gmail.com / Ysn@1874")

if __name__ == "__main__":
    setup()
