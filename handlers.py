# coding=utf-8
# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.appengine.ext import ndb

import os
import webapp2
import logging
import json
import random

from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, 
    TextSendMessage, SourceUser
)
from linebot.utils import PY3

# get channel_secret and channel_access_token from Line Business Center
channel_secret = 'in Line Bussiness Center : messaging api'
channel_access_token = 'in Line Bussiness Center : messaging api'

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)

success_messages = ['你答對拉~', '你是不是有點強', '都給你玩就好拉', '100分']
almost_messages = ['你快成功了', '路遙知馬力', '成功是一分的天才，加上九十九分的努力', "加把勁"]
fail_messages = ['GG拉', '認真點好嗎？', '你有在玩嗎', '你要不要去睡覺', '好拉 加油']


class UserData(ndb.Model):
    user_id = ndb.StringProperty()
    guess_number = ndb.StringProperty()
    

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, I am Line Bot')


class LinebotHandler(webapp2.RequestHandler):
    def post(self):
        # get X-Line-Signature header value
        signature = self.request.headers['X-Line-Signature']
        
        # get request body as text
        body = self.request.body
        logging.info("Request body: " + body)
                
        # parse webhook body
        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            start_response('400 Bad Request', [])
            return create_body('Bad Request')
        
        for event in events:
            if not isinstance(event, MessageEvent):
                continue
            if not isinstance(event.message, TextMessage):
                continue
            if not isinstance(event.source, SourceUser):
                continue

            # get user id
            profile = line_bot_api.get_profile(event.source.user_id)
            logging.info("@user_info // id:" + str(profile.user_id) + ", name:" + str(profile.display_name))
            
            # try to get user data in DB
            results = UserData.query(UserData.user_id == str(profile.user_id)).fetch(1)
            user_data = results[0] if len(results) > 0 else None
            if user_data is None:
                random_v = str(self.gen_answer())
                logging.info("random_v: " + random_v)
                # new user data
                user_data = UserData(
                    user_id=str(profile.user_id),
                    guess_number=random_v,
                )
                user_data.put()
        
            logging.info("user_data in DB // " + user_data.user_id + ", " + user_data.guess_number)
            logging.info("user message // " + event.message.text)
            
            # check user message is command or not
            is_command, user_message = self.handle_command_if_need(event.message.text, user_data)
            if is_command is True:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(user_message)
                )
            else:    
                # handle the game result
                user_message_array = list(event.message.text)
                valid, user_message = self.valid_user_input(user_message_array)
                if valid is True:
                    answer = user_data.guess_number
                    a, b = self.check_answer(user_message_array, answer)
                    user_message = str(a) + " A " + str(b) + " B " + "\n" + self.get_murmur_message(a, b)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=user_message)
                )

        self.response.write("status : ok")

    def get_murmur_message(self, a_count, b_count):
        if a_count is 4:
            return random.choice(success_messages) + "\n要重新玩記得reset喔"
        elif a_count + b_count >= 3:
            return random.choice(almost_messages)
        else:
            return random.choice(fail_messages)

    def handle_command_if_need(self, text, user_data):
        if text == "reset" or text == "Reset" or text == "r" or text == "R":
            random_v = str(self.gen_answer())
            user_data.guess_number = random_v
            user_data.put()

            logging.info("random_v: " + random_v)
            return True, "重設定了唷 可以繼續玩了"
        elif text == "help" or text == "Help" or text == "h" or text == "H":
            message = "我們來玩1A2B ~\n" \
                   "輸入4個不連續數字\n" \
                   "如果要猜新的數字 直接跟我說\n" \
                   "reset, Reset, r 或是 R 都是可以的喔"
            return True, message
        else:
            return False, ""

    def gen_answer(self):
        while 1:
            r = random.randint(1234, 9876)
            #  gen non-repeat number
            if int(r) % 10 != int(r/10) % 10:
                if int(r) % 10 != int(r/100) % 10:
                    if int(r) % 10 != int(r/1000) % 10:
                        if int(r/10) % 10 != int(r/100) % 10:
                            if int(r/10) % 10 != int(r/1000) % 10:
                                if int(r/100) % 10 != int(r/1000) % 10:
                                    return r
                                else:                       
                                    continue
                            else:
                                continue
                        else:
                            continue
                    else:
                        continue
                else:
                    continue
            else:
                continue
                
    def check_answer(self, user_amessage, answer):
        a = 0
        b = 0
        for i in range(4):
            if (str(answer)[i] == user_amessage[i]):
                a += 1
        for j in range(4):
            for k in range(4):
                if (str(answer)[j] == user_amessage[k]):
                    b += 1
        b -= a
        return a, b
    
    def valid_user_input(self, user_message_array):
        if len(user_message_array) is not 4:
            return False, "輸入4個數字啦..."
        elif len(user_message_array) != len(set(user_message_array)):
            return False, "不能重複啦 你會不會玩？"
        else:
            for c in user_message_array:
                if c.isdigit() is False:
                    is_all_digit = False
                    return False, "可以都是數字嗎?"    
        return True, ""