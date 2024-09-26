from django.conf import settings
import asyncio
from common.scripts.DjangoUtils import generate_uuid_hex
from common.scripts.LlmUtils import calc_token, is_tokens_less_than_settings
from common.scripts.PythonCodeUtils import print_color
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
# from google.auth import default as google_default_credentials
import json
import openai
from typing import AsyncGenerator
from .models.ModelNameChoice import MODEL_NAME_CHOICES
from .settings import SEND_MAX_TOKENS
from .tasks import (
    get_history,
    save_message_models, replace_default_room_name,
)
from .Utils import (
    decompression, get_room_settings, is_create_user_room,
)

MODEL_NAME_CHOICES_DICT = dict(MODEL_NAME_CHOICES())


class OpenAIChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        self.connect_user    = self.scope['user']
        self.room_id         = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = 'room_%s' % self.room_id
        
        # ユーザ認証▽
        if self.connect_user.is_anonymous or not self.connect_user or not await is_create_user_room(self.connect_user, self.room_id):
            if settings.DEBUG:
                print_color('info: ERROR: is_anonymous OpenAIChatConsumer.disconnect', 3)
            await self.channel_layer.group_discard(self.room_group_name,
                                                   self.channel_name,)
            await self.close()
            raise StopConsumer()
        elif settings.DEBUG:
            print_color('info: RUN OpenAIChatConsumer.connect', 3)
        # ユーザ認証△
        
        await self.channel_layer.group_add(self.room_group_name,
                                           self.channel_name,)
        await self.accept()

    async def disconnect(self, close_code):
        if settings.DEBUG:
            print_color('info: Run OpenAIChatConsumer.disconnect', 3)
        await self.channel_layer.group_discard(self.room_group_name,
                                               self.channel_name,)
        await self.close()
        raise StopConsumer()

    async def receive(self, text_data=None, bytes_data=None):
        if settings.DEBUG:
            print_color('info: Run OpenAIChatConsumer.receive', 3)
        
        # post データ取得▽
        text_data_json = json.loads(text_data)
        data_dict      = decompression(text_data_json)
        # post データ取得△

        # RoomSettings の取得
        room_settings_dict = await get_room_settings(self.room_id)
        data_dict          = data_dict | room_settings_dict
        
        # model_name の変換
        data_dict['model_name'] = MODEL_NAME_CHOICES_DICT[data_dict['model_name']]
        
        if settings.DEBUG:
            print_color(f'data_dict: {data_dict}', 4)

        # ルームに紐づくヒストリーメッセージ時の取得(celery tasks)
        get_history.delay(self.room_group_name, self.room_id, data_dict)

    async def complete_task_get_history(self, event):
        if settings.DEBUG:
            print_color(f'info: Run OpenAIChatConsumer.complete_task_get_history:\n{event}', 3)
        # ルームに紐づくヒストリーメッセージ時の取得
        data_dict                 = event['response']['data_dict']
        data_dict['history_list'] = event['response']['history_list']
        data_dict['history_text'] = event['response']['history_text']
        
        # 入力のバリデーション▽
        ## 何も質問されてないときに返すテキスト▽
        if data_dict['user_sentence'].replace(' ','').replace('　','') == '':
            error_message = '私は生成AIです。あなたと会話したり、質問に答えたりできます。'
            message_data = {
                'type':       'llm_answer',
                'llm_answer': error_message,
            }
            await self.send(json.dumps(message_data))

        ## 何も質問されてないときに返すテキスト△
        
        ## メッセージのトークンが設定値を超えた場合の処理▽
        elif not is_tokens_less_than_settings(
                    sentence   = data_dict['user_sentence']+data_dict['system_sentence']+data_dict['assistant_sentence']+data_dict['history_text'],
                    max_tokens = int(SEND_MAX_TOKENS)):
            error_message = f'入力文字数が設定値を超えたみたいです。\n過去の会話、システムメッセージなども含めて最大トークンは{SEND_MAX_TOKENS}に設定されています。'
            message_data = {
                'type':       'llm_answer',
                'llm_answer': error_message,
            }
            await self.send(json.dumps(message_data))
        ## メッセージのトークンが設定値を超えた場合の処理△
        # 入力のバリデーション△
        
        # メイン処理
        else:
            llm_answer = await self.chat_generater(
                                            data_dict['user_sentence'],
                                            data_dict['system_sentence'],
                                            data_dict['assistant_sentence'],
                                            history_list      = data_dict['history_list'],
                                            model_name        = data_dict['model_name'],
                                            max_tokens        = data_dict['max_tokens'],
                                            temperature       = data_dict['temperature'],
                                            top_p             = data_dict['top_p'],
                                            frequency_penalty = data_dict['frequency_penalty'],
                                            presence_penalty  = data_dict['presence_penalty'],)
            message_data = {
                'type':       'llm_answer',
                'llm_answer': llm_answer,
            }
            await self.send(json.dumps(message_data))

            data_dict['llm_response'] = llm_answer
            data_dict['message_id']   = generate_uuid_hex()
            tokens_info_dict = {
                'sent_tokens':      calc_token(
                                        sentence = data_dict['user_sentence']+data_dict['system_sentence']+data_dict['assistant_sentence']+data_dict['history_text'],
                                        ),
                'generated_tokens': calc_token(sentence = data_dict['llm_response'],),
            }
            data_dict['tokens_info_dict'] = tokens_info_dict
        
        
            save_message_models.delay(self.room_group_name, self.room_id, data_dict)

    async def complete_task_save_message_models(self, response):
        message_data = {
            'type': 'task_complete__save_model',
        }
        await self.send(json.dumps(message_data))

    async def complete_task_replace_default_room_name(self, response):
        message_data = {
            'type': 'complete_task_replace_default_room_name',
        }
        await self.send(json.dumps(message_data))


    # 回答の生成を行う非同期関数
    async def chat_generater(self,
                             user_sentence:str,
                             system_sentence:str     = None,
                             assistant_sentence:str  = None,
                             *,
                             history_list:list       = None,
                             model_name:str          = 'gpt-3.5-turbo',
                             max_tokens:int          = 256,
                             temperature:float       = 1.0,
                             top_p:float             = 1.0,
                             frequency_penalty:float = 1.0,
                             presence_penalty:float  = 1.0,
                             timeout:int             = 30,
                             asyncio_sleep:float     = 0.03,
                             ) -> str:

        # 想定外のパラメータが設定された場合の処理▽
        if not (0.0 <= temperature <= 2.0) or not (0.0 <= top_p <= 1.0) or not (-2.0 <= presence_penalty <= 2.0) or not (-2.0 <= frequency_penalty <= 2.0):
            raise ValueError("llm parameter values error")
        # 想定外のパラメータが設定された場合の処理△
        
        # gpt-4o 用(ハードコーディングのため適宜関数にいれる前の処理としてもいいかも)
        if model_name.startswith("gpt-4o"):
            asyncio_sleep = 0.01
        
        # プロンプトの生成
        ## ## system_sentence の追加
        messages = [
            {
                'role':    'system',
                'content': system_sentence if system_sentence and system_sentence.replace(' ','').replace('　','') != '' else 'You are an AI assistant that helps people find information.',
            }
        ]
        ## ヒストリーの追加
        if history_list:
            for hist in history_list:
                messages.append(hist)
        ## user_sentence の追加
        messages.append(
            {
                'role':    'user',
                'content': user_sentence,
            }
        )
        ## assistant_sentence の追加
        if assistant_sentence and assistant_sentence.replace(' ','').replace('　','') != '':
            messages.append(
                {
                    'role':    'assistant',
                    'content': assistant_sentence,
                }
            )
        
        # 非同期処理の場合にはclientをUtilでなく定義が必要▽
        if settings.IS_USE_AZURE_OPENAI:
            client = openai.AzureOpenAI(
                                azure_endpoint = settings.AZURE_OPENAI_ENDPOINT,
                                api_key        = settings.OPENAI_API_KEY,
                                api_version    = settings.AZURE_OPENAI_API_VERSION,
                                http_client    = None,) # IF USE ProxyServer httpx.Client(proxies=settings.HTTP_PROXY)))
        else:
            client = openai.OpenAI(api_key     = settings.OPENAI_API_KEY,
                                   http_client = None,) # IF USE ProxyServer httpx.Client(proxies=settings.HTTP_PROXY)))
        # 非同期処理の場合にはclientをUtilでなく定義が必要△
        
        response = client.chat.completions.create(
                            model       = model_name,
                            messages    = messages,
                            temperature = temperature,
                            max_tokens  = max_tokens,
                            stream      = False,
                            timeout     = timeout,)
        return response.choices[0].message.content