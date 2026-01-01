import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "groups": {},
        "users": {}  # Format: {"24085": {"name": "Ahmed", "history": {"GroupA": [1, 5]}}}
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_group_data(data, group_name):
    if group_name not in data['groups']:
        data['groups'][group_name] = {
            "nombre_mission": 0,
            "tasks": {str(i): {"done": False, "user": ""} for i in range(1, 31)}
        }
        save_data(data)
    return data['groups'][group_name]

# --- ROUTES ---

@app.route('/')
def index():
    group_name = request.args.get('group')
    
    if group_name:
        # If group selected, go to Login page
        return redirect(url_for('login', group=group_name))
    else:
        # Show list of groups
        data = load_data()
        groups_list = list(data['groups'].keys())
        return render_template('select_group.html', groups=groups_list)

@app.route('/login')
def login():
    group_name = request.args.get('group')
    if not group_name:
        return redirect(url_for('index'))
    return render_template('login.html', group_name=group_name)

@app.route('/mission')
def mission():
    group_name = request.args.get('group')
    user_id = request.args.get('uid')
    
    if not group_name or not user_id:
        return redirect(url_for('index'))
        
    data = load_data()
    
    # Verify User exists (in case of direct link)
    if user_id not in data['users']:
        return redirect(url_for('login', group=group_name))
    
    group_data = get_group_data(data, group_name)
    user_data = data['users'][user_id]
    
    # Get tasks this user has done in THIS specific group
    my_tasks_in_group = user_data['history'].get(group_name, [])
    
    return render_template('mission.html', 
                           group_name=group_name, 
                           uid=user_id, 
                           my_name=user_data['name'],
                           my_tasks=my_tasks_in_group,
                           data=group_data)

@app.route('/auth', methods=['POST'])
def auth():
    """Login Logic"""
    req = request.json
    group_name = req.get('group')
    user_id = req.get('id')
    user_name = req.get('name').strip()
    
    # Validation: ID must be 5 digits
    if len(user_id) != 5 or not user_id.isdigit():
        return jsonify({"error": "الرقم التعريفي يجب أن يكون 5 أرقام"}), 400
        
    if not user_name:
        return jsonify({"error": "الرجاء إدخال الاسم"}), 400

    data = load_data()
    
    # If new user, save. If existing user, update name (optional) or keep old.
    if user_id not in data['users']:
        data['users'][user_id] = {
            "name": user_name,
            "history": {}
        }
    else:
        # Optional: Update name if they enter a different one
        data['users'][user_id]['name'] = user_name
        
    # Ensure group exists
    get_group_data(data, group_name)
    
    save_data(data)
    return jsonify({"success": True, "uid": user_id})

@app.route('/update_task', methods=['POST'])
def update_task():
    data = load_data()
    req = request.json
    
    group_name = req.get('group_name')
    user_id = req.get('uid')
    task_id = req.get('task_id')
    
    if not group_name or not user_id or not task_id:
        return jsonify({"error": "بيانات ناقصة"}), 400

    group_data = get_group_data(data, group_name)
    task_str = str(task_id)
    
    if task_str in group_data['tasks']:
        if group_data['tasks'][task_str]['done']:
            return jsonify({"error": "تم اختيار هذا الجزء بالفعل!"}), 400
        
        # 1. Update Task
        group_data['tasks'][task_str]['done'] = True
        group_data['tasks'][task_str]['user'] = user_id
        
        # 2. Update User History
        if group_name not in data['users'][user_id]['history']:
            data['users'][user_id]['history'][group_name] = []
        data['users'][user_id]['history'][group_name].append(int(task_id))
        
        # 3. Check Group Completion
        all_done = all(t['done'] for t in group_data['tasks'].values())
        reset_message = ""
        
        if all_done:
            group_data['nombre_mission'] += 1
            # Reset tasks
            for k in group_data['tasks']:
                group_data['tasks'][k] = {"done": False, "user": ""}
            reset_message = "اكتملت الختمه! تم زيادة العداد."
        
        data['groups'][group_name] = group_data
        save_data(data)
            
        return jsonify({
            "success": True, 
            "nombre_mission": group_data['nombre_mission'], 
            "tasks": group_data['tasks'],
            "reset_message": reset_message
        })
        
    return jsonify({"error": "رقم الجزء غير صالح"}), 400

@app.route('/get_status')
def get_status():
    group_name = request.args.get('group')
    if not group_name:
        return jsonify({}), 400
    data = load_data()
    return jsonify(get_group_data(data, group_name))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)