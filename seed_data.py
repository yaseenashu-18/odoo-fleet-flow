from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import random

# MongoDB Connection
client = MongoClient('mongodb://localhost:27017/fleetflow')
db = client.get_database()

# Collections
users_col = db.users
vehicles_col = db.vehicles
trips_col = db.trips
expenses_col = db.expenses
drivers_col = db.drivers
maint_col = db.maintenance

def seed_demo_data():
    # 1. Find the current Admin (Rikshith)
    owner = users_col.find_one({'username': 'rikshith26'})
    if not owner:
        print("User rikshith26 not found. Please login first.")
        return
    
    owner_id = str(owner['_id'])
    print(f"Seeding data for owner: {owner['username']} ({owner_id})")

    # Clear existing data for this owner to start fresh
    vehicles_col.delete_many({'owner_id': owner_id})
    trips_col.delete_many({'owner_id': owner_id})
    expenses_col.delete_many({'owner_id': owner_id})
    drivers_col.delete_many({'owner_id': owner_id})
    maint_col.delete_many({'owner_id': owner_id})
    # Keep users but delete team members added by this owner
    users_col.delete_many({'owner_id': owner_id, 'username': {'$ne': owner['username']}})

    # 2. Add Team Members
    team_members = [
        {'username': 'manikanta_ops', 'role': 'Dispatcher', 'owner_id': owner_id},
        {'username': 'yaseen_mechanic', 'role': 'Maintenance', 'owner_id': owner_id},
    ]
    for member in team_members:
        member['created_at'] = datetime.utcnow()
        users_col.update_one({'username': member['username']}, {'$set': member}, upsert=True)

    # 3. Add Vehicles
    vehicles = [
        {'plate': 'TS 09 EA 4567', 'model': 'Ashok Leyland 3118', 'type': 'Trailer Truck', 'capacity': '20 tons', 'odometer': 45000, 'status': 'On Trip'},
        {'plate': 'KA 01 MG 8899', 'model': 'Tata Prima 4028.S', 'type': 'Container', 'capacity': '15 tons', 'odometer': 12000, 'status': 'Idle'},
        {'plate': 'MH 12 QP 1234', 'model': 'Mahindra Blazo X', 'type': 'Refrigerated', 'capacity': '10 tons', 'odometer': 33000, 'status': 'In Shop'},
        {'plate': 'AP 07 TV 5566', 'model': 'BharatBenz 2823C', 'type': 'Trailer Truck', 'capacity': '25 tons', 'odometer': 8000, 'status': 'Idle'},
    ]
    for v in vehicles:
        v['owner_id'] = owner_id
        v['created_at'] = datetime.utcnow()
        vehicles_col.insert_one(v)

    # 4. Add Drivers
    drivers = [
        {'name': 'Moksha', 'license': 'DL-12345678', 'license_expiry': '2027-12-31', 'completion_rate': 98, 'safety_score': 95, 'complaints': 0, 'status': 'On Duty'},
        {'name': 'Saketh', 'license': 'DL-88776655', 'license_expiry': '2026-06-15', 'completion_rate': 92, 'safety_score': 88, 'complaints': 1, 'status': 'On Duty'},
        {'name': 'Eswar', 'license': 'DL-11223344', 'license_expiry': '2025-01-10', 'completion_rate': 100, 'safety_score': 99, 'complaints': 0, 'status': 'On Duty'},
        {'name': 'Srinivas', 'license': 'DL-55443322', 'license_expiry': '2028-09-20', 'completion_rate': 85, 'safety_score': 72, 'complaints': 3, 'status': 'Resting'},
    ]
    for d in drivers:
        d['owner_id'] = owner_id
        d['created_at'] = datetime.utcnow()
        drivers_col.insert_one(d)

    # 5. Add Trips (Mix of Done, On Trip, Pending)
    origins = ['Hyderabad', 'Mumbai', 'Bangalore', 'Chennai', 'Delhi']
    destinations = ['Pune', 'Ahmedabad', 'Kolkata', 'Kochi', 'Vizag']
    
    # Historical Trips (Done) for Analytics (Last 6 months)
    for i in range(15):
        days_ago = random.randint(10, 180)
        date = datetime.utcnow() - timedelta(days=days_ago)
        trip_id_obj = ObjectId()
        trip = {
            '_id': trip_id_obj,
            'vehicle_id': random.choice(vehicles)['plate'],
            'cargo_weight': random.randint(5000, 20000),
            'driver': random.choice(drivers)['name'],
            'origin': random.choice(origins),
            'destination': random.choice(destinations),
            'fuel_cost': random.randint(8000, 18000),
            'status': 'Done',
            'owner_id': owner_id,
            'created_at': date
        }
        trips_col.insert_one(trip)
        
        # Add Expenses for these trips
        expenses_col.insert_one({
            'trip_id': str(trip_id_obj),
            'driver': trip['driver'],
            'distance': random.randint(300, 1500),
            'fuel_cost': trip['fuel_cost'],
            'misc_cost': random.randint(500, 3000),
            'liters': random.randint(100, 400),
            'status': 'Done',
            'owner_id': owner_id,
            'created_at': date
        })

    # Active Trips
    for i in range(2):
        trip = {
            'vehicle_id': vehicles[i]['plate'],
            'cargo_weight': 12000,
            'driver': drivers[i]['name'],
            'origin': 'Chennai',
            'destination': 'Bangalore',
            'fuel_cost': 14000,
            'status': 'On Trip',
            'owner_id': owner_id,
            'created_at': datetime.utcnow()
        }
        trips_col.insert_one(trip)

    # Pending Cargo Trips
    for i in range(4):
        trip = {
            'vehicle_id': 'Unassigned',
            'cargo_weight': random.randint(2000, 10000),
            'driver': 'Waiting...',
            'origin': random.choice(origins),
            'destination': random.choice(destinations),
            'fuel_cost': 0,
            'status': 'Pending',
            'owner_id': owner_id,
            'created_at': datetime.utcnow()
        }
        trips_col.insert_one(trip)

    # 6. Add Maintenance Logs
    maint_logs = [
        {'vehicle_plate': 'MH 12 QP 1234', 'issue': 'Engine Overheating', 'date': (datetime.utcnow().strftime('%Y-%m-%d')), 'cost': 15000, 'status': 'In Shop'},
        {'vehicle_plate': 'TS 09 EA 4567', 'issue': 'Suspension Tuning', 'date': (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d'), 'cost': 12000, 'status': 'Done'},
        {'vehicle_plate': 'KA 01 MG 8899', 'issue': 'Oil Filter Change', 'date': (datetime.utcnow() - timedelta(days=20)).strftime('%Y-%m-%d'), 'cost': 4500, 'status': 'Done'},
    ]
    for log in maint_logs:
        log['owner_id'] = owner_id
        log['created_at'] = datetime.utcnow()
        maint_col.insert_one(log)

    print("Successfully seeded COMPLETE demo data for hackathon!")

if __name__ == '__main__':
    seed_demo_data()
