# ChickenFryBiryani

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials
import requests
import base64


class TelegramInterface:
    def __init__(self):
        self.access_token = open('telegram_access_token.txt', 'r').read()
        self.captcha_folder = "/home/rob/Captcha/"
        self.captcha_response_folder = "/home/rob/CaptchaResponse/"
        self.captcha_read_folder = '/home/rob/CaptchaRead/'
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet_credentials.json', self.scope)
        self.client = gspread.authorize(self.credentials)
        self.row_entries = {'telegram_name': 'XYZ', 'telegram_id': '00000', 'status': 'active', 'wait_status': 'idle',
                            'sent': 0, 'replied': 0, 'last_sent': '0'*14, 'last_replied': '0'*14}

    def is_added_user(self, user):
        auto_sheet = self.client.open('Telegram Interns').sheet1
        user_cells = auto_sheet.findall(str(user['id']))
        return len(user_cells) != 0

    def update_captcha_history(self, update):
        user = update.message.from_user
        history_sheet = self.client.open('Captcha History').sheet1
        empty_records = history_sheet.findall('', in_column=5)
        for hist in empty_records[::-1]:
            if history_sheet.cell(hist.row, 1).value == str(user['id']):
                history_sheet.update_cell(hist.row, 5, update.message.text.split(' ')[-1])
                history_sheet.update_cell(hist.row, 6, update.message.date.strftime('%Y/%m/%d/%H:%M:%S'))
                break
        return

    def add_user(self, update, context):
        user = update.message.from_user
        manual_sheet = self.client.open('Telegram Intern Info').sheet1
        user_presence = manual_sheet.findall(str(user['id']))
        if len(user_presence) == 0:
            context.bot.send_message(chat_id=user['id'], text='Manual Approval Required.')
            return
        if len(user_presence) > 1:
            context.bot.send_message(chat_id=user['id'], text='Sry. Multiple Instances Found.')
            return
        auto_sheet = self.client.open('Telegram Interns').sheet1
        if self.is_added_user(user):
            context.bot.send_message(chat_id=user['id'], text='Already Added.')
            return
        self.row_entries['telegram_name'], self.row_entries['telegram_id'] = user['first_name'], str(user['id'])
        auto_sheet.append_row(list(self.row_entries.values()))
        context.bot.send_message(chat_id=user['id'], text='Successfully Added.')
        return

    def set_user_inactive(self, update, context):
        user = update.message.from_user
        if not self.is_added_user(user):
            context.bot.send_message(chat_id=user['id'], text='Not Valid User. Get Added First.')
            return
        auto_sheet = self.client.open('Telegram Interns').sheet1
        user_row_id = auto_sheet.find(str(user['id'])).row
        auto_sheet.update_cell(user_row_id, 3, 'inactive')
        context.bot.send_message(chat_id=user['id'], text='You are set to Inactive.')
        return

    def set_user_active(self, update, context):
        user = update.message.from_user
        if not self.is_added_user(user):
            context.bot.send_message(chat_id=user['id'], text='Not Valid User. Get Added First.')
            return
        auto_sheet = self.client.open('Telegram Interns').sheet1
        user_row_id = auto_sheet.find(str(user['id'])).row
        auto_sheet.update_cell(user_row_id, 3, 'active')
        context.bot.send_message(chat_id=user['id'], text='You are set to Active.')
        return

    def save_response(self, update, context):
        user = update.message.from_user
        if not self.is_added_user(user):
            context.bot.send_message(chat_id=user['id'], text='Not Valid User. Get Added First.')
            return
        # response_received = context.args
        response_received = update.message.text.split(' ')
        if len(response_received) != 1:
            print('Invalid Format...')
            return
        auto_sheet = self.client.open('Telegram Interns').sheet1
        user_row_id = auto_sheet.find(str(user['id'])).row
        if auto_sheet.cell(user_row_id, 4).value == 'waiting':
            with open(self.captcha_response_folder + str(user['id']) + '.txt', 'w') as fp:
                fp.write(response_received[0])
            previous_sent_count = int(auto_sheet.cell(user_row_id, 6).value)
            auto_sheet.update_cell(user_row_id, 4, 'idle')
            auto_sheet.update_cell(user_row_id, 8, datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"))
            auto_sheet.update_cell(user_row_id, 6, previous_sent_count+1)
            self.update_captcha_history(update)
            print('Response Received.')
        else:
            context.bot.send_message(chat_id=user['id'], text='Invalid Response. Bot not waiting for your response.')
        return

    def receiver(self):
        updater = Updater(self.access_token, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler('add_me', self.add_user))
        dp.add_handler(CommandHandler('inactive', self.set_user_inactive))
        dp.add_handler(CommandHandler('active', self.set_user_active))
        # dp.add_handler(CommandHandler('x', self.save_response, pass_args=True))
        dp.add_handler(MessageHandler(Filters.text & (~Filters.command), self.save_response))
        updater.start_polling()
        updater.idle()

    def get_effective_telegram_user_id(self):
        # Write Scheduler Algorithm Here
        auto_sheet = self.client.open('Telegram Interns').sheet1
        active_user_rows = list(map(lambda x: x.row, auto_sheet.findall('active', in_column=3)))
        idle_active_user_rows = list(filter(lambda x: auto_sheet.cell(x, 4).value == 'idle', active_user_rows))
        current_time = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        oldest_idle_time = current_time
        oldest_idle_user_id = '0'
        for i in range(len(idle_active_user_rows)):
            temp_time = auto_sheet.cell(idle_active_user_rows[i], 8).value
            if temp_time < oldest_idle_time:
                oldest_idle_time = temp_time
                oldest_idle_user_id = str(auto_sheet.cell(idle_active_user_rows[i], 2).value)
        return oldest_idle_user_id

    def send_captcha(self, captcha_pointer, captcha_type, preset_user_id):
        # Save Captcha into FS First
        current_time = datetime.datetime.utcnow()
        captcha_path = ""
        if captcha_type == 'image':
            captcha_path = self.captcha_folder + captcha_pointer
        # elif captcha_type == 'url':     # You can use this, But preferable not cus of inconsistency.
        #     # Default proxies for secure http browsing for tor
        #     proxy = {'http': 'socks5h://localhost:9050', 'https': 'socks5h://localhost:9050'}
        #     img_response = requests.get(captcha_pointer, proxies=proxy)
        #     with open(captcha_path, 'wb') as fp:
        #         fp.write(img_response.content)
        bot = telegram.Bot(self.access_token)
        if preset_user_id:
            user_telegram_id = preset_user_id
            auto_sheet = self.client.open('Telegram Interns').sheet1
            user_row = auto_sheet.find(user_telegram_id, in_column=2).row
            print('Row:', user_row)
            if auto_sheet.cell(user_row, 4).value == 'waiting':
                print('Busy.')
                return False
        else:
            user_telegram_id = self.get_effective_telegram_user_id()
        if user_telegram_id == '0':
            # No idle user to send captcha
            return False
        bot.sendPhoto(chat_id=int(user_telegram_id), photo=open(captcha_path, 'rb'))
        # Update Sheets
        auto_sheet = self.client.open('Telegram Interns').sheet1
        user_row = auto_sheet.find(user_telegram_id, in_column=2).row
        auto_sheet.update_cell(user_row, 4, 'waiting')
        sent_count = int(auto_sheet.cell(user_row, 5).value)
        auto_sheet.update_cell(user_row, 5, sent_count+1)
        auto_sheet.update_cell(user_row, 7, current_time.strftime("%Y%m%d%H%M%S"))
        history_sheet = self.client.open('Captcha History').sheet1
        history_sheet.append_row([user_telegram_id, captcha_path.split('/')[-1], captcha_type,
                                  current_time.strftime("%Y/%m/%d/%H%M:%S")])
        return user_telegram_id

    def send_message_to_user(self, user_telegram_id, message):
        bot = telegram.Bot(self.access_token)
        bot.send_message(chat_id=user_telegram_id, text=message)
        return True
