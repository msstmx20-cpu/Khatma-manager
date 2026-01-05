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
        "users": {}  # "24085": {"name": "Ahmed", "history": {"GroupA": [1, 5]}}
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_group_data(data, group_name):
    if group_name not in data['groups']:
        data['groups'][group_name] = {
            "nombre_mission": 0,
            # Status: 0=Available, 1=Reserved, 2=Done
            "tasks": {str(i): {"status": 0, "user_id": "", "user_name": ""} for i in range(1, 31)}
        }
        save_data(data)
    return data['groups'][group_name]

# --- ROUTES ---

@app.route('/')
def index():
    group_name = request.args.get('group')
    if group_name:
        return redirect(url_for('login', group=group_name))
    else:
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
    if user_id not in data['users']:
        return redirect(url_for('login', group=group_name))
    
    group_data = get_group_data(data, group_name)
    user_data = data['users'][user_id]
    
    # Get user's specific history count
    my_tasks_count = len(user_data['history'].get(group_name, []))
    
    return render_template('mission.html', 
                           group_name=group_name, 
                           uid=user_id, 
                           my_name=user_data['name'],
                           my_tasks_count=my_tasks_count,
                           data=group_data)

@app.route('/auth', methods=['POST'])
def auth():
    req = request.json
    group_name = req.get('group')
    user_id = req.get('id')
    user_name = req.get('name').strip()
    
    if len(user_id) != 5 or not user_id.isdigit():
        return jsonify({"error": "الرقم التعريفي يجب أن يكون 5 أرقام"}), 400
    if not user_name:
        return jsonify({"error": "الرجاء إدخال الاسم"}), 400

    data = load_data()
    if user_id not in data['users']:
        data['users'][user_id] = {"name": user_name, "history": {}}
    else:
        data['users'][user_id]['name'] = user_name
        
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
    task = group_data['tasks'][task_str]
    
    # SECURITY: Can I touch this task?
    if task['status'] != 0 and task['user_id'] != user_id:
        return jsonify({"error": "هذه المهمة لشخص آخر!"}), 400

    # LOGIC: Cycle Status (0 -> 1 -> 2 -> 0)
    new_status = 0
    user_name = data['users'][user_id]['name']
    
    if task['status'] == 0:
        # Reserve it
        new_status = 1 
    elif task['status'] == 1:
        # Mark as Done
        new_status = 2
        # Add to history
        if group_name not in data['users'][user_id]['history']:
            data['users'][user_id]['history'][group_name] = []
        if task_id not in data['users'][user_id]['history'][group_name]:
             data['users'][user_id]['history'][group_name].append(int(task_id))
    elif task['status'] == 2:
        # Cancel (Release)
        new_status = 0
        # Remove from history
        if group_name in data['users'][user_id]['history']:
             if int(task_id) in data['users'][user_id]['history'][group_name]:
                 data['users'][user_id]['history'][group_name].remove(int(task_id))

    # Update Task
    task['status'] = new_status
    
    if new_status > 0:
        task['user_id'] = user_id
        task['user_name'] = user_name
    else:
        task['user_id'] = ""
        task['user_name'] = ""

    # Check Group Completion (Only if all are 2)
    all_done = all(t['status'] == 2 for t in group_data['tasks'].values())
    reset_message = ""
    
    if all_done:
        group_data['nombre_mission'] += 1
        # Reset tasks
        for k in group_data['tasks']:
            group_data['tasks'][k] = {"status": 0, "user_id": "", "user_name": ""}
        reset_message = "اكتملت المهمة! تم زيادة العداد."
    
    save_data(data)
        
    return jsonify({
        "success": True, 
        "nombre_mission": group_data['nombre_mission'], 
        "tasks": group_data['tasks'],
        "reset_message": reset_message
    })

@app.route('/get_status')
def get_status():
    group_name = request.args.get('group')
    if not group_name:
        return jsonify({}), 400
    data = load_data()
    return jsonify(get_group_data(data, group_name))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
