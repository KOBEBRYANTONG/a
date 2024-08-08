from flask import Flask, render_template, request, redirect, url_for
import requests
import json
import time
import threading

app = Flask(__name__)

# Read Discord user tokens from file
with open("tokenn.txt", "r") as file:
    tokens = [line.strip() for line in file.readlines()]

stop_event = threading.Event()
send_thread = None

def send_message(token, channel_id, message, delay, counter):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    data = {
        "content": message
    }
    success = False
    retries = 0

    while not success and retries < 3:
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
            response.raise_for_status()
            success = True
        except requests.exceptions.RequestException as e:
            print(f"Error sending message from token {token}: {message}\n{e}")
            if "429" in str(e):
                time.sleep(15)
                retries += 1
            else:
                retries = 3

    return "success" if success else "failed"

def send_messages_worker(messages, channel_id, delay, counter):
    tokens_len = len(tokens)
    token_index = 0

    while True:
        if stop_event.is_set():
            break

        for message in messages:
            if stop_event.is_set():
                break

            token = tokens[token_index]
            result = send_message(token, channel_id, f"{message} {counter}", delay, counter)
            token_index += 1
            if token_index >= tokens_len:
                token_index = 0

            if result == "success":
                counter += 1
                if counter > 10000:
                    counter = 1
            elif result == "failed":
                pass

        if not stop_event.is_set():
            time.sleep(0.1)

@app.route('/', methods=['GET', 'POST'])
def index():
    global send_thread
    if request.method == 'POST':
        channel_id = request.form.get('channel_id')
        messages = request.form.get('messages').split('\n')
        delay = float(request.form.get('delay'))
        if channel_id and messages:
            if send_thread is None or not send_thread.is_alive():
                global stop_event
                stop_event.clear()
                counter = 1
                send_thread = threading.Thread(target=send_messages_worker, args=(messages, channel_id, delay, counter))
                send_thread.start()
            return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/stop')
def stop():
    global send_thread
    if send_thread and send_thread.is_alive():
        stop_event.set()
        send_thread.join()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
