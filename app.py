from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps
import os
import pandas as pd
import json

app = Flask(__name__)
app.secret_key = "nyx_super_secret_key"

# SQLite configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'nyx.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"connect_args": {"timeout": 15}}

db = SQLAlchemy(app)

# --- LOAD NUTRITION DATASET (FOOD + SUPPLEMENTS) ---
NUTRITION_DB = []
try:
    # 1. Load Foods
    food_path = os.path.join(os.path.dirname(__file__), 'docs', 'Food.xlsx')
    if os.path.exists(food_path):
        df_food = pd.read_excel(food_path)
        for _, row in df_food.iterrows():
            NUTRITION_DB.append({
                'name': str(row['Food Name']),
                'category': str(row.get('Category', 'General')),
                'calories': int(row['Calories (kcal/100g)']),
                'protein': float(row['Protein (g)']),
                'carbs': float(row['Carbs (g)']),
                'fats': float(row.get('Fat (g)', 0)),
                'source': 'food'
            })
    
    # 2. Load Supplements
    supp_path = os.path.join(os.path.dirname(__file__), 'docs', 'supplements_dataset.xlsx')
    if os.path.exists(supp_path):
        df_supp = pd.read_excel(supp_path)
        for _, row in df_supp.iterrows():
            NUTRITION_DB.append({
                'name': str(row['Supplement Name']),
                'category': str(row.get('Type', 'Supplement')),
                'calories': int(row.get('Calories (per serving)', 0)),
                'protein': float(row.get('Protein (g)', 0)),
                'carbs': float(row.get('Carbs (g)', 0)),
                'fats': 0.0, # Usually minimal in powders
                'source': 'supplement'
            })
    
    print(f"Successfully synchronized {len(NUTRITION_DB)} items (Foods & Supplements).")
except Exception as e:
    print(f"Error loading nutrition datasets: {e}")

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    nickname = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    profile_setup_complete = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    plan = db.Column(db.String(20), default='Elite') # Trial, Starter, Pro, Elite
    trial_start = db.Column(db.DateTime, default=datetime.utcnow)
    
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    height = db.Column(db.String(20), nullable=True)
    weight = db.Column(db.String(20), nullable=True)
    goal = db.Column(db.String(80), nullable=True)
    
    last_login_at = db.Column(db.DateTime, nullable=True)
    daily_wake_up_at = db.Column(db.String(20), nullable=True)
    
    # Nutrition Progression
    nutrition_goal = db.Column(db.String(20), default='Maintain') # Bulk, Cut, Maintain
    nutrition_week = db.Column(db.Integer, default=1)
    nutrition_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Assigned Intelligence
    assigned_workout = db.Column(db.Text, nullable=True) # JSON string

    logs = db.relationship('ProgressLog', backref='athlete', lazy=True)
    prs = db.relationship('PersonalRecord', backref='athlete', lazy=True)
    goals = db.relationship('PRGoal', backref='athlete', lazy=True)
    messages = db.relationship('ChatMessage', backref='athlete', lazy=True)

    @property
    def trial_days_left(self):
        if self.plan != 'Trial': return 0
        delta = datetime.utcnow() - self.trial_start
        return max(0, 30 - delta.days)
        
    @property
    def has_premium_access(self):
        # We've removed premium access for now, so everyone has it.
        return True

class ProgressLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False) # YYYY-MM-DD
    weight = db.Column(db.String(20), nullable=True)
    cals = db.Column(db.String(20), nullable=True)
    protein = db.Column(db.String(20), nullable=True)
    carbs = db.Column(db.String(20), nullable=True)
    fats = db.Column(db.String(20), nullable=True)
    steps = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PersonalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    exercise = db.Column(db.String(80), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_pr = db.Column(db.Boolean, default=False)  # Was this a new PR when logged?

class PRGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise = db.Column(db.String(80), nullable=False)
    target_weight = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False) # 'admin' or 'athlete'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    protocol_name = db.Column(db.String(100))
    duration_mins = db.Column(db.Integer, default=0)
    total_volume = db.Column(db.Float, default=0.0)
    logs = db.relationship('WorkoutLog', backref='session', lazy=True)

class WorkoutLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    sets_data = db.Column(db.Text, nullable=False) # JSON: [{"reps": 10, "weight": 100}, ...]
    intensity_score = db.Column(db.Integer, default=0) # 1-10 RPE


class DailyNutritionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    meal_type = db.Column(db.String(20), nullable=False) # Breakfast, Lunch, Dinner, Snacks
    calories = db.Column(db.Integer, default=0)
    protein = db.Column(db.Float, default=0.0)
    carbs = db.Column(db.Float, default=0.0)
    fats = db.Column(db.Float, default=0.0)
    serving = db.Column(db.String(50), default='1 serving')
    date = db.Column(db.String(20), nullable=False) # YYYY-MM-DD
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class SystemAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), default='info') # info, warning, tactical
    message = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

class WaterLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, default=0.0) # in liters
    date = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class WorkoutTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    # JSON list of {name, sets, target}
    exercises_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize database
with app.app_context():
    db.create_all()
    
    # Seed Admin User if none exist
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            email="admin@nyxft.com",
            name="System Admin",
            nickname="admin",
            password="admin", # Plaintext for demo
            is_admin=True,
            profile_setup_complete=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user seeded: admin@nyxft.com / admin")


# --- ROUTING ---

@app.route('/')
def index():
    user = None
    if 'user' in session:
        user = User.query.filter_by(email=session['user']).first()
    return render_template('client/index.html', user=user)

@app.route('/auth')
def auth():
    mode = request.args.get('mode', 'login')
    return render_template('client/auth.html', mode=mode)

@app.route('/profile-setup')
def profile_setup():
    if 'user' not in session:
        return redirect(url_for('auth'))
    return render_template('client/profile-setup.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('client/forgot_password.html')

@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('auth'))
    user = User.query.filter_by(email=session['user']).first()
    return render_template('client/chat.html', user=user)


@app.route('/coaches')
def coaches():
    if 'user' not in session:
        return redirect(url_for('auth'))
    user = User.query.filter_by(email=session['user']).first()
    if not user: return redirect(url_for('auth'))
    return render_template('client/coaches.html', user=user, messages=user.messages, premium_locked=not user.has_premium_access)

@app.route('/pr-tracker')
def pr_tracker():
    if 'user' not in session:
        return redirect(url_for('auth'))
    user = User.query.filter_by(email=session['user']).first()
    if not user: return redirect(url_for('auth'))

    all_logs = user.prs[::-1]  # newest first

    # ── KEY LIFTS: compute current PR, previous PR, delta for each 
    KEY_EXERCISES = ['Bench Press', 'Squat', 'Deadlift']
    key_lifts = []
    for ex in KEY_EXERCISES:
        records = sorted([p for p in user.prs if p.exercise.lower() == ex.lower()], key=lambda x: x.weight)
        current = records[-1].weight if records else None
        previous = records[-2].weight if len(records) >= 2 else None
        delta = round(current - previous, 1) if current and previous else None
        goal_obj = PRGoal.query.filter_by(user_id=user.id, exercise=ex).first()
        goal = goal_obj.target_weight if goal_obj else None
        pct = round((current / goal) * 100) if current and goal else 0
        key_lifts.append({
            'exercise': ex,
            'current': current,
            'previous': previous,
            'delta': delta,
            'goal': goal,
            'pct': min(pct, 100)
        })

    # ── PER-EXERCISE PR MAP (best weight per exercise)
    pr_map = {}
    for p in user.prs:
        ex_key = p.exercise.lower()
        if ex_key not in pr_map or p.weight > pr_map[ex_key]['weight']:
            pr_map[ex_key] = {'exercise': p.exercise, 'weight': p.weight, 'date': p.date}

    # ── WEEKLY PROGRESS BARS (last 6 weeks' best for Bench Press)
    from collections import defaultdict
    weekly = defaultdict(float)
    for p in user.prs:
        if 'bench' in p.exercise.lower():
            week_key = p.date[:6] if len(p.date) > 5 else p.date  # crude bucketing
            weekly[week_key] = max(weekly[week_key], p.weight)
    weekly_bars = sorted(weekly.items())[-6:] if weekly else []
    max_w = max([v for _, v in weekly_bars], default=1)
    weekly_chart = [{'label': k, 'height': int((v / max_w) * 110)} for k, v in weekly_bars]

    # ── INSIGHTS
    insights = []
    for ex in KEY_EXERCISES:
        records = sorted([p for p in user.prs if p.exercise.lower() == ex.lower()], key=lambda x: x.weight)
        if len(records) >= 2:
            diff = round(records[-1].weight - records[-2].weight, 1)
            if diff > 0:
                insights.append(f"📈 You improved your {ex} by {diff}kg — keep the momentum!")
            elif diff == 0:
                insights.append(f"⚡ Your {ex} is holding steady. Push for that next level.")
            else:
                insights.append(f"🔄 Your {ex} had a lighter session. Recovery is progress too.")
    if len(user.prs) >= 5:
        insights.append("🔥 You've logged 5+ sessions — your consistency is building elite strength.")
    if not insights:
        insights.append("💡 Log your first workout to unlock personalized strength insights.")

    # ── BIG 4 BESTS
    best_bench = db.session.query(db.func.max(PersonalRecord.weight)).filter_by(user_id=user.id, exercise='Bench Press').scalar() or 0
    best_squat = db.session.query(db.func.max(PersonalRecord.weight)).filter_by(user_id=user.id, exercise='Squat').scalar() or 0
    best_deadlift = db.session.query(db.func.max(PersonalRecord.weight)).filter_by(user_id=user.id, exercise='Deadlift').scalar() or 0
    best_ohp = db.session.query(db.func.max(PersonalRecord.weight)).filter_by(user_id=user.id, exercise='Overhead Press').scalar() or 0

    # ── HERO STATS (RESTORING)
    total_prs = len([p for p in user.prs if p.is_pr])
    total_logs = len(user.prs)
    best_lift = max([p.weight for p in user.prs], default=0)
    best_lift_ex = next((p.exercise for p in sorted(user.prs, key=lambda x: x.weight, reverse=True)), '—')
    goals_list = PRGoal.query.filter_by(user_id=user.id).all()

    return render_template('client/pr_tracker.html',
        user=user,
        prs=all_logs[:20],
        key_lifts=key_lifts,
        weekly_chart=weekly_chart,
        insights=insights,
        total_prs=total_prs,
        total_logs=total_logs,
        best_lift=best_lift,
        best_lift_ex=best_lift_ex,
        goals=goals_list,
        best_bench=best_bench,
        best_squat=best_squat,
        best_deadlift=best_deadlift,
        best_ohp=best_ohp,
        premium_locked=not user.has_premium_access
    )


@app.route('/nutrition')
def nutrition():
    if 'user' not in session:
        return redirect(url_for('auth'))
    user = User.query.filter_by(email=session['user']).first()
    if not user: return redirect(url_for('auth'))
    
    today = datetime.now().strftime("%Y-%m-%d")
    food_items = DailyNutritionLog.query.filter_by(user_id=user.id, date=today).all()
    water = WaterLog.query.filter_by(user_id=user.id, date=today).first()
    
    # Calculate totals
    totals = {
        'calories': sum(item.calories for item in food_items),
        'protein': sum(item.protein for item in food_items),
        'carbs': sum(item.carbs for item in food_items),
        'fats': sum(item.fats for item in food_items),
        'water': water.amount if water else 0.0
    }
    
    # Define targets (can be dynamic based on user profile)
    targets = {
        'calories': 2500,
        'protein': 180,
        'carbs': 300,
        'fats': 70,
        'water': 4.0
    }
    
    # Group by meal
    meals = {
        'Breakfast': [i for i in food_items if i.meal_type == 'Breakfast'],
        'Lunch': [i for i in food_items if i.meal_type == 'Lunch'],
        'Dinner': [i for i in food_items if i.meal_type == 'Dinner'],
        'Snacks': [i for i in food_items if i.meal_type == 'Snacks']
    }
    
    return render_template('client/nutrition.html', user=user, meals=meals, totals=totals, targets=targets)

@app.route('/settings')
def settings():
    if 'user' not in session: return redirect(url_for('auth'))
    user = User.query.filter_by(email=session['user']).first()
    return render_template('client/settings.html', user=user)

@app.route('/workouts')
def workouts():
    if 'user' not in session: return redirect(url_for('auth'))
    user = User.query.filter_by(email=session['user']).first()
    return render_template('client/workouts.html', user=user)

@app.route('/api/workout/save', methods=['POST'])
def save_workout():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    data = request.json
    
    session_record = WorkoutSession(
        user_id=user.id,
        date=datetime.now().strftime("%Y-%m-%d"),
        protocol_name=data.get('protocol'),
        duration_mins=data.get('duration'),
        total_volume=data.get('volume', 0)
    )
    db.session.add(session_record)
    db.session.commit()
    
    for log in data.get('logs', []):
        new_log = WorkoutLog(
            session_id=session_record.id,
            exercise_name=log['exercise'],
            sets_data=log['sets'],
            intensity_score=log.get('rpe', 0)
        )
        db.session.add(new_log)
        
        # --- SYNC TO PERSONAL RECORDS FOR ANALYTICS ---
        try:
            sets = json.loads(log['sets'])
            for s in sets:
                pr = PersonalRecord(
                    date=datetime.now().strftime("%b %d, %Y"),
                    exercise=log['exercise'],
                    weight=float(s['weight']),
                    reps=int(s['reps']),
                    user_id=user.id,
                    is_pr=False
                )
                db.session.add(pr)
        except Exception as e:
            print(f"Sync error: {e}")
    
    db.session.commit()
    return jsonify({'success': True})



@app.route('/analytics')
def analytics():
    if 'user' not in session:
        return redirect(url_for('auth'))
    
    user = User.query.filter_by(email=session['user']).first()
    if not user: return redirect(url_for('auth'))
    
    # ── LOG DATA EXTRACTION ──
    logs = user.logs
    weight_history = []
    step_history = []
    labels = []
    
    for l in logs[-30:]: # Max 30 days
        labels.append(l.date)
        try: weight_history.append(float(l.weight or 0))
        except: weight_history.append(0)
        try: step_history.append(int(l.steps or 0))
        except: step_history.append(0)

    # ── STRENGTH INTEL ──
    prs = user.prs
    max_lifts = {}
    for p in prs:
        ex = p.exercise.lower()
        if ex not in max_lifts or p.weight > max_lifts[ex]['weight']:
            max_lifts[ex] = {'name': p.exercise, 'weight': p.weight, 'date': p.date}
    
    # Volume by movement type (Simplified logic)
    volume = {'Push': 0, 'Pull': 0, 'Legs': 0}
    for p in prs:
        ex = p.exercise.lower()
        if any(x in ex for x in ['bench', 'overhead', 'press', 'dip']): volume['Push'] += p.weight * p.reps
        elif any(x in ex for x in ['row', 'pull', 'chin', 'curl', 'deadlift']): volume['Pull'] += p.weight * p.reps
        elif any(x in ex for x in ['squat', 'lunge', 'leg', 'extension']): volume['Legs'] += p.weight * p.reps

    # ── PREDICTIVE ETA (Elite only) ──
    eta_days = "—"
    if len(weight_history) >= 7 and user.goal:
        try:
            # Simple linear prediction based on first/last of recent logs
            start_w = weight_history[0]
            end_w = weight_history[-1]
            diff = end_w - start_w
            if diff != 0:
                target_w = float(''.join(c for c in user.goal if c.isdigit() or c=='.'))
                remaining = target_w - end_w
                days = (remaining / diff) * len(weight_history)
                if days > 0:
                    eta_date = datetime.now() + timedelta(days=int(days))
                    eta_days = eta_date.strftime("%b %d, %Y")
        except: pass

    # ── CONSISTENCY PULSE ──
    consistency_data = [1 if l.weight and l.cals else 0.5 for l in logs[-20:]]

    return render_template('client/analytics.html', 
        user=user,
        labels=labels,
        weight_history=weight_history,
        step_history=step_history,
        max_lifts=max_lifts,
        volume=volume,
        eta_days=eta_days,
        consistency_data=consistency_data
    )

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('auth'))
    
    user = User.query.filter_by(email=session['user']).first()
    if not user:
        return redirect(url_for('auth'))
        
    # --- AUTOMATIC WAKE-UP DETECTION ---
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    if not user.last_login_at or user.last_login_at.strftime("%Y-%m-%d") != today_str:
        user.daily_wake_up_at = now.strftime("%H:%M")
        user.last_login_at = now
        db.session.commit()
    
    # --- STATS CALCULATION ---
    user_logs = user.logs
    user_prs = user.prs
    
    # Calculate streak (days with steps >= 10000)
    streak = 0
    for l in reversed(user_logs):
        try:
            if int(l.steps or 0) >= 10000:
                streak += 1
            else:
                break
        except: break

    def safe_float(v, default=0.0):
        try:
            return float(''.join(c for c in str(v) if c.isdigit() or c=='.'))
        except:
            return default

    def safe_int(v, default=0):
        try:
            return int(''.join(c for c in str(v) if c.isdigit()))
        except:
            return default

    # Weight trend
    weight_trend = 0
    if len(user_logs) >= 2:
        curr_w = safe_float(user_logs[-1].weight)
        prev_w = safe_float(user_logs[-2].weight)
        if curr_w and prev_w:
            weight_trend = round(curr_w - prev_w, 1)

    # Chart Data
    weekly_steps = [0] * 7
    weekly_weight = [0] * 7
    for i in range(7):
        d = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
        l = ProgressLog.query.filter_by(user_id=user.id, date=d).first()
        if not l:
            d_legacy = (datetime.now() - timedelta(days=6-i)).strftime("%b %d")
            l = ProgressLog.query.filter_by(user_id=user.id, date=d_legacy).first()
        
        if l:
            weekly_steps[i] = safe_int(l.steps)
            weekly_weight[i] = safe_float(l.weight)

    # Activity Timeline
    timeline = []
    for pr in user_prs[-5:]:
        timeline.append({
            'type': 'workout',
            'title': f'Logged {pr.exercise}',
            'desc': f'{pr.weight}kg x {pr.reps} reps',
            'time': pr.date,
            'icon': 'ph-barbell'
        })
    for l in user_logs[-3:]:
        if l.weight:
            timeline.append({
                'type': 'weight',
                'title': 'Weight Updated',
                'desc': f'{l.weight}kg',
                'time': l.date,
                'icon': 'ph-scales'
            })
    timeline = sorted(timeline, key=lambda x: x['time'], reverse=True)[:6]

    stats = {
        'main_insight': "You achieved your step goal 3 days in a row! Keep the momentum. 🔥" if streak >= 3 else "Protocol synchronized. All vital signs normal. Focusing on performance metrics.",
        'latest_weight': safe_float(user_logs[-1].weight) if user_logs else safe_float(user.weight),
        'latest_steps': safe_int(user_logs[-1].steps) if user_logs else 0,
        'step_goal': 10000,
        'streak': streak,
        'weight_trend': weight_trend,
        'consistency': '0%',
        'weekly_steps': weekly_steps,
        'weekly_weight': weekly_weight,
        'recent_pr': ('No Intel' if not user_prs else
                      f"{max(user_prs, key=lambda p: p.weight).exercise} · {max(user_prs, key=lambda p: p.weight).weight}kg"),
        'timeline': timeline,
        'recent_workouts': user_prs[-3:][::-1]
    }

    if user_logs:
        stats['consistency'] = f"{min(100, int((len(user_logs) / 7) * 100))}%"
        chart_data = []
        for l in user_logs[-7:]:
            s_val = float(l.steps or 0)
            height = min(180, max(20, int((s_val / 10000) * 180)))
            chart_data.append(height)
        while len(chart_data) < 7:
            chart_data.insert(0, 20)
        stats['chart_heights'] = chart_data

    return render_template('client/dashboard.html', 
                           user=user, 
                           stats=stats)


# --- API ENDPOINTS ---

@app.route('/api/log', methods=['POST'])
def api_log():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    user = User.query.filter_by(email=session['user']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    today_str = datetime.now().strftime("%b %d")
    existing_log = ProgressLog.query.filter_by(user_id=user.id, date=today_str).first()
    
    weight = data.get('weight')
    steps = data.get('steps')
    
    if existing_log:
        if weight is not None:
            if existing_log.weight:
                return jsonify({'error': 'Weight protocol already synchronized for this 24h cycle.'}), 400
            existing_log.weight = weight
        if steps is not None:
            existing_log.steps = steps
    else:
        new_log = ProgressLog(
            date=today_str,
            weight=weight,
            steps=steps or 0,
            user_id=user.id,
            created_at=datetime.utcnow()
        )
        db.session.add(new_log)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/pr', methods=['POST'])
def api_pr():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    user = User.query.filter_by(email=session['user']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    exercise = data.get('exercise', '').strip()
    new_weight = float(data.get('weight', 0))
    new_reps = int(data.get('reps', 1))

    # Check if this is a new PR (beats previous best)
    prev_best = db.session.query(db.func.max(PersonalRecord.weight)).filter_by(
        user_id=user.id, exercise=exercise
    ).scalar()
    is_new_pr = prev_best is None or new_weight > prev_best

    log = PersonalRecord(
        date=datetime.now().strftime("%b %d, %Y"),
        exercise=exercise,
        weight=new_weight,
        reps=new_reps,
        user_id=user.id,
        is_pr=is_new_pr
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'success': True, 'is_new_pr': is_new_pr, 'exercise': exercise, 'weight': new_weight})

@app.route('/api/pr/goal', methods=['POST'])
def api_pr_goal():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    user = User.query.filter_by(email=session['user']).first()
    if not user: return jsonify({'error': 'User not found'}), 404
    exercise = data.get('exercise', '').strip()
    target = float(data.get('target', 0))
    goal = PRGoal.query.filter_by(user_id=user.id, exercise=exercise).first()
    if goal:
        goal.target_weight = target
    else:
        goal = PRGoal(exercise=exercise, target_weight=target, user_id=user.id)
        db.session.add(goal)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/pr/data')
def api_pr_data():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    if not user: return jsonify([])
    logs = [{'exercise': p.exercise, 'weight': p.weight, 'reps': p.reps, 'date': p.date, 'is_pr': p.is_pr}
            for p in user.prs[-20:]]
    return jsonify(logs)

@app.route('/api/auth', methods=['POST'])
def api_auth():
    data = request.json
    action = data.get('action')
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and passcode required'}), 400

    if action == 'signup':
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User already exists'}), 400
            
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Full name is required for signup'}), 400
            
        new_user = User(
            email=email,
            name=name,
            nickname=name,
            password=password # Note: plaintext only for demo scope
        )
        db.session.add(new_user)
        db.session.commit()
        session['user'] = email
        return jsonify({'success': True, 'redirect': url_for('profile_setup')})
        
    elif action == 'login':
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['user'] = email
            if not user.profile_setup_complete:
                return jsonify({'success': True, 'redirect': url_for('profile_setup')})
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return jsonify({'error': 'Invalid action'}), 400


@app.route('/api/workout/template', methods=['POST'])
def save_template():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    data = request.json
    
    template = WorkoutTemplate(
        user_id=user.id,
        name=data.get('name'),
        exercises_data=json.dumps(data.get('exercises'))
    )
    db.session.add(template)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/workout/templates')
def get_templates():
    if 'user' not in session: return jsonify([]), 401
    user = User.query.filter_by(email=session['user']).first()
    templates = WorkoutTemplate.query.filter_by(user_id=user.id).all()
    
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'exercises': json.loads(t.exercises_data)
    } for t in templates])

@app.route('/api/chat/send', methods=['POST'])
def api_chat_send():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    data = request.json
    
    new_msg = ChatMessage(
        sender='athlete',
        text=data.get('message'),
        time=datetime.now().strftime("%H:%M"),
        user_id=user.id
    )
    db.session.add(new_msg)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/profile', methods=['POST'])
def api_profile():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    user = User.query.filter_by(email=session['user']).first()
    
    if user:
        user.age = data.get('age')
        user.gender = data.get('gender')
        user.height = data.get('height')
        user.weight = data.get('weight')
        user.goal = data.get('goal')
        user.profile_setup_complete = True
        db.session.commit()
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
        
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/settings/update', methods=['POST'])
def api_settings_update():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    data = request.json
    
    if 'nickname' in data: user.nickname = data['nickname']
    if 'goal' in data: user.goal = data['goal']
    if 'weight' in data: user.weight = str(data['weight'])
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/settings/security', methods=['POST'])
def api_settings_security():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    data = request.json
    
    old_p = data.get('old_pass')
    new_p = data.get('new_pass')
    conf_p = data.get('conf_pass')
    
    if user.password != old_p:
        return jsonify({'error': 'CURRENT PASSCODE INVALID'}), 400
    if new_p != conf_p:
        return jsonify({'error': 'PASSCODE MISMATCH'}), 400
        
    user.password = new_p
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True, 'redirect': url_for('auth')})

# --- CONSOLIDATED NUTRITION & HYDRATION API ---

@app.route('/api/nutrition/data')
def get_daily_data():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    if not user: return jsonify({'error': 'User not found'}), 404
    
    today = datetime.now().strftime("%Y-%m-%d")
    food_items = DailyNutritionLog.query.filter_by(user_id=user.id, date=today).all()
    water = WaterLog.query.filter_by(user_id=user.id, date=today).first()
    
    totals = {
        'calories': sum(item.calories for item in food_items),
        'protein': sum(item.protein for item in food_items),
        'carbs': sum(item.carbs for item in food_items),
        'fats': sum(item.fats for item in food_items),
        'water': water.amount if water else 0.0
    }
    
    # Group food items by meal for the UI
    meals = {'Breakfast': [], 'Lunch': [], 'Dinner': [], 'Snacks': []}
    for item in food_items:
        if item.meal_type in meals:
            meals[item.meal_type].append({
                'id': item.id,
                'name': item.name,
                'calories': item.calories,
                'protein': item.protein,
                'carbs': item.carbs,
                'fats': item.fats
            })

    # Calculate TDEE and Targets
    try:
        bw = float(''.join(c for c in (user.weight or "75") if c.isdigit() or c=='.'))
    except:
        bw = 75.0
    
    tdee = int(bw * 33)
    goal = user.nutrition_goal or 'Maintain'
    week = user.nutrition_week or 1
    
    target_cals = tdee
    adjustment = 0
    
    if goal == 'Cut':
        adjustments = [300, 400, 500, 500]
        adj_val = adjustments[min(week-1, 3)]
        target_cals = tdee - adj_val
        adjustment = -adj_val
    elif goal == 'Bulk':
        adjustments = [300, 350, 400, 400]
        adj_val = adjustments[min(week-1, 3)]
        target_cals = tdee + adj_val
        adjustment = adj_val
        
    targets = {
        'calories': target_cals,
        'protein': int(bw * 2.2),
        'carbs': int((target_cals * 0.45) / 4), # 45% Carbs
        'fats': int((target_cals * 0.25) / 9),  # 25% Fats
        'water': 4.0 # 4 Liters
    }

    return jsonify({
        'totals': totals,
        'meals': meals,
        'targets': targets,
        'progression': {
            'goal': goal, 'week': week, 'tdee': tdee, 'adjustment': adjustment
        }
    })

@app.route('/api/nutrition/add', methods=['POST'])
def add_food():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    data = request.json
    
    new_item = DailyNutritionLog(
        name=data.get('name'),
        meal_type=data.get('meal_type'),
        calories=int(data.get('calories', 0)),
        protein=float(data.get('protein', 0)),
        carbs=float(data.get('carbs', 0)),
        fats=float(data.get('fats', 0)),
        date=datetime.now().strftime("%Y-%m-%d"),
        user_id=user.id
    )
    db.session.add(new_item)
    db.session.commit()
    return get_daily_data()

@app.route('/api/nutrition/water', methods=['POST'])
def update_water():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    amount = float(request.json.get('amount', 0))
    today = datetime.now().strftime("%Y-%m-%d")
    
    log = WaterLog.query.filter_by(user_id=user.id, date=today).first()
    if log:
        log.amount = max(0, log.amount + amount)
    else:
        log = WaterLog(amount=max(0, amount), date=today, user_id=user.id)
        db.session.add(log)
    
    db.session.commit()
    return get_daily_data()
@app.route('/api/nutrition/remove', methods=['POST'])
def remove_food():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    item_id = request.json.get('id')
    item = DailyNutritionLog.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        return get_daily_data()
    return jsonify({'error': 'Item not found'}), 404

@app.route('/api/nutrition/set_goal', methods=['POST'])
def set_nutrition_goal():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(email=session['user']).first()
    data = request.json
    new_goal = data.get('goal')
    user.nutrition_goal = new_goal
    user.nutrition_week = 1
    db.session.commit()
    return jsonify({'success': True, 'message': f'Switched to {new_goal} mode. Cycle reset.'})
from functools import wraps

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.password == password and user.is_admin:
            session['admin_user'] = email
            return jsonify({'success': True})
        return jsonify({'error': 'Unauthorized'}), 401
    
    return render_template('admin/admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('user', None)
    return redirect(url_for('admin_login'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user' not in session:
            return redirect(url_for('admin_login'))
        user = User.query.filter_by(email=session['admin_user']).first()
        if not user or not user.is_admin:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/broadcast', methods=['POST'])
@admin_required
def admin_broadcast():
    data = request.json
    msg = data.get('message')
    alert_type = data.get('type', 'info')
    
    if msg:
        new_alert = SystemAlert(message=msg, type=alert_type)
        db.session.add(new_alert)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/admin/alerts/clear/<int:alert_id>', methods=['POST'])
@admin_required
def clear_alert(alert_id):
    alert = SystemAlert.query.get_or_404(alert_id)
    alert.active = False
    db.session.commit()
    return jsonify({'success': True})

def get_flagged_athletes():
    # Detect athletes who haven't logged in 3 days or have 0 weight
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    flagged = []
    
    # 1. Inactivity Flag
    inactive = User.query.filter((User.last_login_at < three_days_ago) | (User.last_login_at == None)).all()
    for u in inactive:
        flagged.append({'user': u, 'reason': 'INACTIVITY', 'severity': 'warning'})
        
    # 2. Weight Anomaly (Legacy check - weight missing)
    missing_weight = User.query.filter((User.weight == None) | (User.weight == '')).all()
    for u in missing_weight:
        if u not in [f['user'] for f in flagged]:
            flagged.append({'user': u, 'reason': 'BIOMETRIC_GAP', 'severity': 'tactical'})
            
    return flagged

# --- CHAT API ENDPOINTS ---

@app.route('/api/chat/send', methods=['POST'])
def api_send_message():
    data = request.json
    user_id = data.get('user_id')
    content = data.get('content')
    sender = data.get('sender') # 'admin' or 'athlete'
    
    if not all([user_id, content, sender]):
        return jsonify({'error': 'Missing data'}), 400
        
    msg = ChatMessage(user_id=user_id, content=content, sender=sender)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/chat/history/<int:user_id>')
def api_chat_history(user_id):
    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp.asc()).all()
    return jsonify([{
        'sender': m.sender,
        'content': m.content,
        'timestamp': m.timestamp.strftime('%H:%M')
    } for m in messages])

@app.route('/admin')
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_logs = DailyNutritionLog.query.count()
    recent_users = User.query.order_by(User.id.desc()).limit(5).all()
    
    # New Intelligence Data
    flagged = get_flagged_athletes()
    active_alerts = SystemAlert.query.filter_by(active=True).order_by(SystemAlert.id.desc()).all()
    
    # Stats
    premium_users = User.query.filter(User.plan != 'Trial').count()
    
    return render_template('admin/admin_dashboard.html', 
                           total_users=total_users, 
                           total_logs=total_logs,
                           recent_users=recent_users,
                           premium_users=premium_users,
                           nutrition_count=len(NUTRITION_DB),
                           flagged_athletes=flagged[:5],
                           active_alerts=active_alerts)

@app.route('/admin/chat')
@admin_required
def admin_chat():
    target_id = request.args.get('user_id')
    athletes = User.query.filter_by(is_admin=False).all()
    return render_template('admin/admin_chat.html', athletes=athletes, target_id=target_id)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/admin_users.html', users=users)

@app.route('/admin/users/toggle_admin/<int:user_id>', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    # Prevent self-demotion if necessary, but keep it simple for now
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"Updated privileges for {user.name}", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    # Delete all associated data
    DailyNutritionLog.query.filter_by(user_id=user.id).delete()
    ProgressLog.query.filter_by(user_id=user.id).delete()
    PersonalRecord.query.filter_by(user_id=user.id).delete()
    PRGoal.query.filter_by(user_id=user.id).delete()
    WaterLog.query.filter_by(user_id=user.id).delete()
    ChatMessage.query.filter_by(user_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    flash(f"Athlete {user.name} and all associated intelligence purged.", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/athlete/<int:user_id>')
@admin_required
def admin_athlete_profile(user_id):
    target_user = User.query.get_or_404(user_id)
    # Get stats for charts
    logs = ProgressLog.query.filter_by(user_id=user_id).order_by(ProgressLog.date.asc()).all()
    prs = PersonalRecord.query.filter_by(user_id=user_id).order_by(PersonalRecord.date.desc()).all()
    
    # Weights for chart
    weights = [float(l.weight or 0) for l in logs if l.weight]
    dates = [l.date for l in logs if l.weight]
    
    return render_template('admin/admin_athlete_profile.html', 
                           target_user=target_user,
                           logs=logs,
                           prs=prs,
                           weights=weights,
                           dates=dates)

@app.route('/admin/assign_workout', methods=['POST'])
@admin_required
def assign_workout():
    data = request.json
    user_id = data.get('user_id')
    workout_data = data.get('workout') # Muscle, Type, Duration
    
    user = User.query.get_or_404(user_id)
    user.assigned_workout = json.dumps(workout_data)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Workout assigned to {user.name}'})

@app.route('/admin/modify_nutrition', methods=['POST'])
@admin_required
def admin_modify_nutrition():
    data = request.json
    user_id = data.get('user_id')
    new_goal = data.get('goal')
    
    user = User.query.get_or_404(user_id)
    user.nutrition_goal = new_goal
    user.nutrition_week = 1
    user.nutrition_updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Nutrition goal for {user.name} updated to {new_goal}'})

@app.route('/admin/nutrition')
@admin_required
def admin_nutrition():
    # Show stats about the dataset
    foods = [i for i in NUTRITION_DB if i['source'] == 'food']
    supps = [i for i in NUTRITION_DB if i['source'] == 'supplement']
    
    return render_template('admin/admin_nutrition.html', 
                           foods_count=len(foods),
                           supps_count=len(supps),
                           total_count=len(NUTRITION_DB))

@app.route('/admin/workouts')
@admin_required
def admin_workouts():
    # Define static training architectures for the oversight view
    muscle_groups = ['Chest', 'Back', 'Legs', 'Shoulders', 'Arms']
    exercises = {
        'Chest': [{'name': 'Bench Press', 'sets': 4, 'reps': 8}, {'name': 'Incline Fly', 'sets': 3, 'reps': 12}],
        'Back': [{'name': 'Deadlift', 'sets': 5, 'reps': 5}, {'name': 'Lat Pulldown', 'sets': 4, 'reps': 10}],
        'Legs': [{'name': 'Squat', 'sets': 4, 'reps': 10}, {'name': 'Leg Press', 'sets': 3, 'reps': 15}]
    }
    training_styles = [
        {'name': 'Compound Training', 'desc': 'Primary force development through multi-joint protocols.', 'workouts': 142},
        {'name': 'Hypertrophy Phase', 'desc': 'Volume-centric architectures for metabolic overload.', 'workouts': 86},
        {'name': 'Powerbuilding', 'desc': 'Hybrid system combining force and aesthetic evolution.', 'workouts': 210}
    ]
    athletes = User.query.limit(10).all()
    
    return render_template('admin/admin_workouts.html', 
                           muscle_groups=muscle_groups,
                           exercises=exercises,
                           training_styles=training_styles,
                           athletes=athletes)

@app.route('/foods')
def get_foods():
    return jsonify(NUTRITION_DB)

if __name__ == '__main__':
    # Run on 5002 to avoid conflicts with other apps
    app.run(debug=True, port=5002)
