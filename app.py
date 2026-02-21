from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fleetflow_secret_key_123')
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/fleetflow')
client = MongoClient(MONGO_URI)
db = client.get_database()

# Collections
users_collection = db.users
users_collection.create_index("username", unique=True)
vehicles_collection = db.vehicles
trips_collection = db.trips
maintenance_collection = db.maintenance
expenses_collection = db.expenses
drivers_collection = db.drivers

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.role = user_data.get('role', 'user')
        self.owner_id = user_data.get('owner_id')

    @property
    def business_id(self):
        # The 'Business ID' is the ID of the Boss.
        # Admins are the Boss, everyone else has an 'owner_id' pointing to their Boss.
        return self.id if self.role == 'Admin' else self.owner_id

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = users_collection.find_one({'username': username})
        
        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            user_obj = User(user_data)
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('Error: Username can only contain letters, numbers, and underscores (_).', 'danger')
            return redirect(url_for('register'))
            
        if users_collection.find_one({'username': username}):
            flash('Username already exists', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            users_collection.insert_one({
                'username': username,
                'password': hashed_password,
                'role': role,
                'created_at': datetime.utcnow()
            })
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Role-Based Redirection
    if current_user.role == 'Driver':
        # Find trips assigned to this driver name
        assigned_trips = list(trips_collection.find({'driver': current_user.username}).sort('created_at', -1))
        driver_profile = drivers_collection.find_one({'name': current_user.username}) or {}
        
        return render_template('driver_dashboard.html', 
                             trips=assigned_trips, 
                             profile=driver_profile)

    # Fetch KPIs using the shared Business ID
    owner_query = {'owner_id': current_user.business_id}
    active_fleet = vehicles_collection.count_documents({**owner_query, 'status': 'On Trip'})
    maintenance_alerts = vehicles_collection.count_documents({**owner_query, 'status': 'In Shop'})
    pending_cargo = trips_collection.count_documents({**owner_query, 'status': 'Pending'})
    
    total_vehicles = vehicles_collection.count_documents(owner_query)
    util_rate = round((active_fleet / total_vehicles * 100), 1) if total_vehicles > 0 else 0
    
    recent_trips = list(trips_collection.find(owner_query).sort('created_at', -1).limit(5))
    for t in recent_trips:
        t['_id'] = str(t['_id'])
        
    return render_template('dashboard.html', 
                          active_fleet=active_fleet,
                          maintenance_alerts=maintenance_alerts,
                          pending_cargo=pending_cargo,
                          util_rate=util_rate,
                          recent_trips=recent_trips)

@app.route('/team')
@login_required
def team():
    if current_user.role != 'Admin':
        flash('Only owners can manage the team.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Find all users who belong to this owner's business (excluding the owner themselves)
    business_team = list(users_collection.find({'owner_id': current_user.business_id}))
    return render_template('team.html', team=business_team)

@app.route('/team/add', methods=['GET', 'POST'])
@login_required
def add_team_member():
    if current_user.role != 'Admin':
        flash('Only owners can manage the team.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if users_collection.find_one({'username': username}):
            flash('Username already exists!', 'danger')
        else:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            users_collection.insert_one({
                'username': username,
                'password': hashed_pw,
                'role': role,
                'owner_id': current_user.business_id, # LINK TO THE BUSINESS
                'created_at': datetime.utcnow()
            })

            # If they added a Driver role, create a basic performance profile too
            if role == 'Driver':
                drivers_collection.insert_one({
                    'name': username,
                    'license': 'Pending',
                    'license_expiry': (datetime.utcnow().replace(year=datetime.utcnow().year + 1)).strftime('%Y-%m-%d'),
                    'completion_rate': 100,
                    'safety_score': 100,
                    'complaints': 0,
                    'status': 'On Duty',
                    'owner_id': current_user.business_id,
                    'created_at': datetime.utcnow()
                })

            flash(f'Team member {username} added successfully!', 'success')
            return redirect(url_for('team'))
            
    return render_template('add_member.html')

@app.route('/api/stats')
@login_required
def get_stats():
    # Use the shared business_id for everyone in the company
    query = {'owner_id': current_user.business_id}
    
    active_fleet = vehicles_collection.count_documents({**query, 'status': 'On Trip'})
    maintenance_alerts = vehicles_collection.count_documents({**query, 'status': 'In Shop'})
    pending_cargo = trips_collection.count_documents({**query, 'status': 'Pending'})
    
    total_vehicles = vehicles_collection.count_documents(query)
    util_rate = round((active_fleet / total_vehicles * 100), 1) if total_vehicles > 0 else 0
    
    return jsonify({
        'active_fleet': active_fleet,
        'maintenance_alerts': maintenance_alerts,
        'pending_cargo': pending_cargo,
        'util_rate': util_rate
    })

@app.route('/vehicles')
@login_required
def vehicles():
    # Show vehicles for the entire business
    vehicles_list = list(vehicles_collection.find({'owner_id': current_user.business_id}))
    for v in vehicles_list:
        v['_id'] = str(v['_id'])
    return render_template('vehicles.html', vehicles=vehicles_list)

@app.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        vehicle_data = {
            'plate': request.form.get('plate'),
            'model': request.form.get('model'),
            'type': request.form.get('type'),
            'capacity': request.form.get('capacity'),
            'odometer': request.form.get('odometer'),
            'status': 'Idle',
            'owner_id': current_user.business_id, # Link to the Business ID
            'created_at': datetime.utcnow()
        }
        vehicles_collection.insert_one(vehicle_data)
        flash('Vehicle added successfully!', 'success')
        return redirect(url_for('vehicles'))
    
    return render_template('add_vehicle.html')

@app.route('/trips', methods=['GET', 'POST'])
@login_required
def trips():
    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        cargo_weight = float(request.form.get('cargo_weight', 0))
        
        # Validation Rule: Prevent trip if CargoWeight > MaxCapacity
        vehicle = vehicles_collection.find_one({'_id': ObjectId(vehicle_id)})
        # Extract number from capacity string like "5 tons"
        import re
        capacity_str = vehicle.get('capacity', '0')
        capacity_val = float(re.findall(r'\d+', capacity_str)[0]) if re.findall(r'\d+', capacity_str) else 0
        if 'ton' in capacity_str.lower():
            capacity_val *= 1000 # Convert tons to kg
            
        if cargo_weight > capacity_val:
            flash(f'Validation Error: Cargo weight ({cargo_weight}kg) exceeds vehicle capacity ({capacity_val}kg)!', 'danger')
            return redirect(url_for('trips'))

        trip_data = {
            'vehicle_id': vehicle['plate'],
            'cargo_weight': cargo_weight,
            'driver': request.form.get('driver'),
            'origin': request.form.get('origin'),
            'destination': request.form.get('destination'),
            'fuel_cost': float(request.form.get('fuel_cost', 0)),
            'status': 'On Trip',
            'owner_id': current_user.business_id,
            'created_at': datetime.utcnow()
        }
        trips_collection.insert_one(trip_data)
        
        # Update vehicle status
        vehicles_collection.update_one({'_id': ObjectId(vehicle_id)}, {'$set': {'status': 'On Trip'}})
        
        flash('Trip dispatched successfully!', 'success')
        return redirect(url_for('trips'))
    
    # Filter everything by this owner
    owner_query = {'owner_id': current_user.business_id}
    trips_list = list(trips_collection.find(owner_query))
    available_vehicles = list(vehicles_collection.find({**owner_query, 'status': 'Idle'}))
    available_drivers = list(drivers_collection.find({**owner_query, 'status': 'On Duty'}))
    
    # Filter drivers with expired licenses (Safety Lock Rule)
    available_drivers = [d for d in available_drivers if datetime.strptime(d['license_expiry'], '%Y-%m-%d') > datetime.now()]
    
    for t in trips_list:
        t['_id'] = str(t['_id'])
    for v in available_vehicles:
        v['_id'] = str(v['_id'])
    for d in available_drivers:
        d['_id'] = str(d['_id'])
        
    return render_template('trips.html', trips=trips_list, vehicles=available_vehicles, drivers=available_drivers)

@app.route('/expenses')
@login_required
def expenses():
    # Simple logic for driver to see their own expenses too if needed, but owners see theirs
    query = {'owner_id': current_user.business_id} if current_user.role != 'Driver' else {'driver': current_user.username}
    expense_list = list(expenses_collection.find(query).sort('created_at', -1))
    for e in expense_list:
        e['_id'] = str(e['_id'])
    return render_template('expenses.html', expenses=expense_list)

@app.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        expense_data = {
            'trip_id': request.form.get('trip_id'),
            'driver': request.form.get('driver'),
            'distance': float(request.form.get('distance', 0)),
            'fuel_cost': float(request.form.get('fuel_cost', 0)),
            'misc_cost': float(request.form.get('misc_cost', 0)),
            'liters': float(request.form.get('liters', 0)),
            'status': 'Done',
            'owner_id': current_user.business_id,
            'created_at': datetime.utcnow()
        }
        expenses_collection.insert_one(expense_data)
        flash('Expense recorded successfully!', 'success')
        return redirect(url_for('expenses'))
    
    return render_template('add_expense.html')

@app.route('/drivers')
@login_required
def drivers():
    # Only show drivers belonging to this business
    driver_list = list(drivers_collection.find({'owner_id': current_user.business_id}))
    for d in driver_list:
        d['_id'] = str(d['_id'])
        expiry_date = datetime.strptime(d['license_expiry'], '%Y-%m-%d')
        d['is_expired'] = expiry_date < datetime.now()
        
    return render_template('drivers.html', drivers=driver_list)

@app.route('/drivers/add', methods=['GET', 'POST'])
@login_required
def add_driver():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        
        # 1. Create a Login Account for the driver
        if users_collection.find_one({'username': name}):
            flash('Error: A user with this name already exists. Pick a different name for the driver.', 'danger')
            return redirect(url_for('add_driver'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        users_collection.insert_one({
            'username': name,
            'password': hashed_password,
            'role': 'Driver',
            'owner_id': current_user.business_id, # Link this driver account to the Boss
            'created_at': datetime.utcnow()
        })
        
        # 2. Create the Driver Performance Profile
        driver_data = {
            'name': name,
            'license': request.form.get('license'),
            'license_expiry': request.form.get('expiry'),
            'completion_rate': 100,
            'safety_score': 100,
            'complaints': 0,
            'status': 'On Duty',
            'owner_id': current_user.business_id, # Link profile to the Boss
            'created_at': datetime.utcnow()
        }
        drivers_collection.insert_one(driver_data)
        
        flash(f'Success! Account created for {name}. They can now login.', 'success')
        return redirect(url_for('drivers'))
    
    return render_template('add_driver.html')

@app.route('/analytics')
@login_required
def analytics():
    # Performance & Financial Calculations ONLY FOR THIS BUSINESS
    owner_query = {'owner_id': current_user.business_id}
    
    expenses = list(expenses_collection.find(owner_query))
    total_fuel_cost = sum(e.get('fuel_cost', 0) for e in expenses)
    
    maintenance_docs = list(maintenance_collection.find(owner_query))
    total_maint_cost = sum(m.get('cost', 0) for m in maintenance_docs)
    
    # Assume fixed revenue per completed trip (example: 1.5 Lakhs per trip)
    completed_trips = trips_collection.count_documents({**owner_query, 'status': 'Done'})
    total_revenue = completed_trips * 150000 
    
    # Calculate Fleet ROI (Simple)
    total_cost = total_fuel_cost + total_maint_cost
    fleet_roi = round(((total_revenue - total_cost) / total_cost * 100), 1) if total_cost > 0 else 0
    
    # Utilization Calculation
    active = vehicles_collection.count_documents({**owner_query, 'status': 'On Trip'})
    total = vehicles_collection.count_documents(owner_query)
    util_rate = round((active / total * 100), 1) if total > 0 else 0

    # Aggregate Monthly Data
    from collections import defaultdict
    monthly_stats = defaultdict(lambda: {'revenue': 0, 'fuel': 0, 'maint': 0})
    
    # Mocking historical months if DB is empty for visuals, but adding real data
    for e in expenses:
        month = e['created_at'].strftime('%b')
        monthly_stats[month]['fuel'] += e.get('fuel_cost', 0)
        monthly_stats[month]['revenue'] += 50000 
        
    for m in maintenance_docs:
        m_date = m.get('date')
        if isinstance(m_date, str) and m_date:
            try:
                month = datetime.strptime(m_date, '%Y-%m-%d').strftime('%b')
            except:
                month = m['created_at'].strftime('%b')
        else:
            month = m['created_at'].strftime('%b')
        monthly_stats[month]['maint'] += float(m.get('cost', 0))

    monthly_data = []
    for month, stats in monthly_stats.items():
        monthly_data.append({
            'month': month,
            'revenue': stats['revenue'],
            'fuel': stats['fuel'],
            'maint': stats['maint'],
            'profit': stats['revenue'] - (stats['fuel'] + stats['maint'])
        })
    
    if not monthly_data:
        # Fallback for visual continuity if store is empty
        monthly_data = [{'month': datetime.now().strftime('%b'), 'revenue': 0, 'fuel': 0, 'maint': 0, 'profit': 0}]

    fuel_efficiency = []
    for e in expenses:
        if e.get('liters') and e.get('distance'):
            fuel_efficiency.append({'month': e['created_at'].strftime('%b'), 'val': round(e['distance']/e['liters'], 2)})

    return render_template('analytics.html', 
                          total_fuel_cost=total_fuel_cost,
                          fleet_roi=fleet_roi,
                          util_rate=util_rate,
                          monthly_data=monthly_data,
                          fuel_efficiency=fuel_efficiency)

@app.route('/maintenance')
@login_required
def maintenance():
    # Filter by business
    owner_query = {'owner_id': current_user.business_id}
    logs = list(maintenance_collection.find(owner_query).sort('created_at', -1))
    vehicles_list = list(vehicles_collection.find(owner_query))
    
    for log in logs:
        log['_id'] = str(log['_id'])
    for v in vehicles_list:
        v['_id'] = str(v['_id'])
        
    return render_template('maintenance.html', logs=logs, vehicles=vehicles_list)

@app.route('/maintenance/add', methods=['GET', 'POST'])
@login_required
def add_maintenance():
    owner_query = {'owner_id': current_user.business_id}
    vehicles_list = list(vehicles_collection.find(owner_query))
    for v in vehicles_list:
        v['_id'] = str(v['_id'])

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        
        # 1. Look up vehicle info
        v = vehicles_collection.find_one({'_id': ObjectId(vehicle_id)})
        
        maint_data = {
            'vehicle_id': vehicle_id,
            'vehicle_plate': v.get('plate', 'N/A') if v else 'N/A',
            'issue': request.form.get('issue'),
            'date': request.form.get('date'),
            'cost': float(request.form.get('cost', 0)),
            'status': 'In Shop',
            'owner_id': current_user.business_id,
            'created_at': datetime.utcnow()
        }
        maintenance_collection.insert_one(maint_data)
        
        # Update vehicle status
        vehicles_collection.update_one({'_id': ObjectId(vehicle_id)}, {'$set': {'status': 'In Shop'}})
        
        flash('Maintenance log created!', 'success')
        return redirect(url_for('maintenance'))
    
    return render_template('add_repair.html', vehicles=vehicles_list)

if __name__ == '__main__':
    # Running with use_reloader=False for stability on Windows systems
    app.run(debug=True, use_reloader=False)
