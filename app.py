import gevent  # (Websocket support)
from gevent import monkey  # (Websocket support)
monkey.patch_all()  # (Websocket support) This patch should be carried out as early as possible.

from flask import Flask, render_template
from flask import request
from flask_socketio import SocketIO, emit # (Websocket support)

from models.brightness import Brightness
from models.gpio import GPIO
from models.serial_port import SerialPort
from models.buzzer import Buzzer
from models.can_bus import CanBus

app = Flask(__name__)
socketio = SocketIO(app, async_mode="gevent")

dev_gpio = GPIO()
dev_rs232 = SerialPort(name="rs232")
dev_rs485 = SerialPort(name="rs485")
dev_brightness = Brightness()
dev_buzzer = Buzzer()
dev_can_bus = CanBus()

@app.route("/")
def home():
    return render_template('home.html')

# Brightness
@app.route('/brightness', methods=['GET', 'POST'])
def brightness():
    if request.method == 'GET':
        actual_brightness = dev_brightness.get_actual_brightness()
        return render_template('brightness.html', actual_brightness=actual_brightness)
    if request.method == 'POST':
        new_brightness = request.form["brightness"]
        dev_brightness.set_brightness(brightness=new_brightness)
        actual_brightness = dev_brightness.get_actual_brightness()
        return render_template('brightness.html', actual_brightness=actual_brightness)

@app.route('/api/brightness', methods=['POST'])
def api_brightness():
    new_brightness = request.form["brightness"]
    dev_brightness.set_brightness(brightness=new_brightness)
    actual_brightness = dev_brightness.get_actual_brightness()
    return {"brightness": actual_brightness}

# GPIO
@app.route("/gpio")
def gpio():
    in_1 = "Unknown"
    in_2 = "Unknown"
    in_3 = "Unknown"
    in_4 = "Unknown"
    return render_template('gpio.html', in_1=in_1, in_2=in_2, in_3=in_3, in_4=in_4)

@app.route('/api/gpio/<gpioX>', methods=['GET', 'POST'])
def api_gpio(gpioX):
    if request.method == 'GET':
        msg = dev_gpio.input(inputX=gpioX)
        if msg:
            return { gpioX: msg }
        return { gpioX: "Not a valid Chipsee CM4 GPIO port." }

    if request.method == 'POST':
        req = request.json
        v_out = int(req['v_out'])
        msg = dev_gpio.output(outputX=gpioX, value=v_out)
        if msg == True:
            return { 'status': 'Success', 'msg': gpioX }
        return { 'status': 'Error', 'msg': msg }

# Buzzer
@app.route("/buzzer")
def buzzer():
    return render_template('buzzer.html')

@app.route('/api/buzzer', methods=['POST'])
def api_buzzer():
    req = request.json
    new_status = str(req['buzzer'])
    msg = dev_buzzer.set_to(new_status)
    if msg == True:
        return { 'status': 'Success', 'msg': new_status }
    return { 'status': 'Error', 'msg': msg }

# Serial
@app.route("/rs232")
def rs232():
    return render_template('rs232.html')

@socketio.on('rs232_tx')
def rs232_tx(data):
    print(data)
    dev_rs232.tx(data.get('data'))

def rs232_rx():
    while True:
        data = dev_rs232.rx()
        if data:
            socketio.emit('rs232_rx', { 'data': data })
gevent.spawn(rs232_rx) # background task to read 232 device

@app.route("/rs485")
def rs485():
    return render_template('rs485.html')

@socketio.on('rs485_tx')
def rs485_tx(data):
    dev_rs485.tx(data.get('data'))

def rs485_rx():
    while True:
        data = dev_rs485.rx()
        if data:
            socketio.emit('rs485_rx', { 'data': data })
gevent.spawn(rs485_rx) # background task to read 485 device

# CAN Bus
@app.route("/can_bus")
def can_bus():
    return render_template('can_bus.html')

@socketio.on('can_send')
def can_send(data):
    dev_can_bus.send(data)

def can_recv():
    if not dev_can_bus.bus:
        return
    for msg in dev_can_bus.bus:
        socketio.emit('can_recv', { 'data': str(msg) })
gevent.spawn(can_recv) # background task to read CAN device

if __name__ == '__main__':
    socketio.run(app, debug=True)
