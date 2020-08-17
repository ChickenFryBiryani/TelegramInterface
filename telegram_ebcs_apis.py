# ChickenFryBiryani

import os
import flask
from flask import request
from telegram_Interface import TelegramInterface

app = flask.Flask(__name__)
app.config['DEBUG'] = True


@app.route('/send_captcha', methods=['GET'])
def send_captcha_api():
    parameters = request.args.to_dict()
    if 'captcha_pointer' in parameters:
        captcha_pointer = parameters['captcha_pointer']
    else:
        return {'success': False, 'error': "Captcha Pointer Argument Missing."}
    if 'captcha_type' in parameters:
        captcha_type = parameters['captcha_type']
    else:
        return {'success': False, 'error': "Captcha Type Missing."}
    preset_user_id = None
    if 'preset_user_id' in parameters:
        preset_user_id = parameters['preset_user_id']
    telegram_helper = TelegramInterface()
    telegram_response = telegram_helper.send_captcha(captcha_pointer, captcha_type, preset_user_id=preset_user_id)
    if not telegram_response:
        return {'success': True, 'message': "All Captcha Responders are busy."}
    return {'success': True, 'user_telegram_id': telegram_response}


@app.route('/get_captcha_response', methods=['GET'])
def get_captcha_response_api():
    parameters = request.args.to_dict()
    if 'response_id' not in parameters:
        return {'success': False, 'error': "Response Filename is missing."}
    captcha_response_folder = '/home/rob/CaptchaResponse/'
    captcha_read_folder = '/home/rob/CaptchaRead/'
    response_filename = parameters['response_id'] + '.txt'
    if not os.path.isfile(captcha_response_folder + response_filename):
        return {'success': True, 'error': "No response yet"}
    response = open(captcha_response_folder + response_filename, 'r').read()
    os.system('mv {}{} {}{}'.format(captcha_response_folder, response_filename, captcha_read_folder, response_filename))
    return {'success': True, 'response': response}


@app.route('/send_message_to_user', methods=['GET'])
def send_message_api():
    parameters = request.args.to_dict()
    if 'user_telegram_id' not in parameters:
        return {'error': "Telegram Id missing."}
    if 'message' not in parameters:
        return {'error': "Message missing."}
    telegram_helper = TelegramInterface()
    try:
        telegram_helper.send_message_to_user(parameters['user_telegram_id'], parameters['message'])
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.route('/start_scraper', methods=['GET'])
def start_scraper_in_system():
    parameters = request.args.to_dict()
    if 'market' not in parameters:
        return {'success': False, 'error': 'Market not specified.'}
    if 'system' not in parameters:
        return {'success': False, 'error': 'System not specified.'}
    system_no = parameters['system']
    run_cmd = '/usr/bin/python3.6 /home/rob/PycharmProjects/DarknetMarketScrapers/scraper_sql_{}.py'.format(system_no)
    start_cmd = "sshpass -p '{}' ssh rob@192.168.247.{} '{}'".format('ebcs747', system_no, run_cmd)
    os.system(start_cmd)


app.run(host="0.0.0.0")
