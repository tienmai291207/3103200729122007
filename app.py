from flask import Flask, jsonify, request, redirect, url_for
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import secrets
import string
from datetime import datetime, timedelta
import time
import threading

app = Flask(__name__)

engine = create_engine('sqlite:///ip_keys.db', echo=True)
Base = declarative_base()

class IPKey(Base):
    __tablename__ = 'ip_keys'
    id = Column(Integer, primary_key=True)
    ip = Column(String, unique=True)
    key = Column(String)
    creation_time = Column(DateTime)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def generate_10_char_key():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))

def clean_expired_keys():
    while True:
        current_time = time.time()
        session = Session()
        for stored_ip_key in session.query(IPKey).all():
            creation_time = stored_ip_key.creation_time
            if current_time - creation_time.timestamp() >= 86400:
                session.delete(stored_ip_key)
        session.commit()
        session.close()
        time.sleep(3600)

cleanup_thread = threading.Thread(target=clean_expired_keys)
cleanup_thread.daemon = True
cleanup_thread.start()

@app.route('/keys', methods=['GET'])
def redirect_to_ip():
    user_ip = request.remote_addr  
    return redirect(url_for('get_ip_data', ip=user_ip))

@app.route('/keys/ip/<ip>', methods=['GET'])
def get_ip_data(ip):
    session = Session()
    stored_ip_key = session.query(IPKey).filter_by(ip=ip).first()

    if stored_ip_key:
        key = stored_ip_key.key
    else:
        key = generate_10_char_key()
        new_ip_key = IPKey(ip=ip, key=key, creation_time=datetime.now())
        session.add(new_ip_key)
        session.commit()

    session.close()

    return redirect(url_for('get_ip_data_with_key', ip=ip, key=f'Sang_{key}'))

@app.route('/keys/ip/<ip>/<key>', methods=['GET'])
def get_ip_data_with_key(ip, key):
    session = Session()
    stored_ip_key = session.query(IPKey).filter_by(ip=ip).first()

    if stored_ip_key and key == f'Sang_{stored_ip_key.key}':
        creation_time = stored_ip_key.creation_time
        current_time = datetime.now()
        time_difference = int(86400 - (current_time - creation_time).total_seconds())  
        hours, remainder = divmod(time_difference, 3600)
        minutes, seconds = divmod(remainder, 60)

        remaining_time = f"{hours}:{minutes}:{seconds}"

        data = {
            "ip": ip,
            "key": key,
            "time": remaining_time
        }
    else:
        data = {'message': f'IP {ip} No Key.'}

    session.close()

    return jsonify(data)

@app.route('/add_key/ip/<ip>', methods=['POST'])
def add_key(ip):
    if request.method == 'POST':
        new_key = request.form.get('custom_key') 

        if not new_key:
            return jsonify({'message': 'Custom key not provided'})

        session = Session()
        stored_ip_key = session.query(IPKey).filter_by(ip=ip).first()

        if stored_ip_key:
            stored_ip_key.key = new_key
        else:
            new_ip_key = IPKey(ip=ip, key=new_key, creation_time=datetime.now())
            session.add(new_ip_key)

        session.commit()
        session.close()

        return jsonify({'message': 'Custom key added successfully', 'new_key': new_key})

    return jsonify({'message': 'Invalid request method'})

@app.route('/delete_key/ip/<ip>', methods=['POST'])
def delete_key(ip):
    if request.method == 'POST':
        session = Session()
        stored_ip_key = session.query(IPKey).filter_by(ip=ip).first()

        if stored_ip_key:
            session.delete(stored_ip_key)
            session.commit()
            session.close()
            return jsonify({'message': 'Key for IP {} has been deleted.'.format(ip)})
        else:
            session.close()
            return jsonify({'message': 'IP {} does not exist in the database.'.format(ip)})

    return jsonify({'message': 'Invalid request method'})

@app.route('/all_keys', methods=['GET'])
def view_all_keys():
    session = Session()
    all_keys = session.query(IPKey).all()

    keys_data = []
    for stored_ip_key in all_keys:
        keys_data.append({
            "ip": stored_ip_key.ip,
            "key": stored_ip_key.key,
            "creation_time": stored_ip_key.creation_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    session.close()

    return jsonify(keys_data)

if __name__ == '__main__':
    app.run(debug=True)