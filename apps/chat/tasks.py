from django.conf import settings
from asgiref.sync import async_to_sync
from celery import shared_task
from celery.utils.log import get_task_logger
from channels.layers import get_channel_layer
from common.scripts.LlmUtils import Llm, text_modify_fnc
from common.scripts.PythonCodeUtils import print_color
import json
from typing import Dict, List, Optional
from .models import Message, Room, RoomSettings
from .settings import DEFAULT_ROOM_NAME, MAX_LEN_ROOM_NAME
from .Utils import NextQuestionAssistantPrompt

logger = get_task_logger(__name__)

@shared_task(max_retries                = 1,     # リトライ回数
             task_acks_late             = True,  # Task 終了後に Ask する
             task_reject_on_worker_lost = False, # Worker 異常終了時に再実行する
             visibility_timeout         = 360,   # Ack されない Task の再スケジューリング(sec)
             worker_prefetch_multiplier = 1,     # Task のプリフェッチ数(default:4)
             )
def get_history(room_group_name:str,
                room_id:str,
                data_dict:dict,
                history_len:int = 3,
                ) -> Optional[List[Dict[str, str]]]:
    # ルームに紐づくヒストリーメッセージ時の取得
    channel_layer = get_channel_layer()

    if history_len != 0:
        return_history_list = []
        message_objects     = Message.objects.filter(room_id__room_id = room_id,
                                                     is_active        = True,
                                                     ).order_by('-date_create')[:history_len]
        return_history_text = ''
        for message_object in reversed(message_objects):
            # return_history_list
            history_dict_tmp            = {}
            history_dict_tmp['role']    = 'user'
            history_dict_tmp['content'] = message_object.user_message
            return_history_list.append(history_dict_tmp)
            
            history_dict_tmp            = {}
            history_dict_tmp['role']    = 'assistant'
            history_dict_tmp['content'] = message_object.llm_response
            return_history_list.append(history_dict_tmp)
            
            # return_history_text
            return_history_text += f'## HUMAN ({message_object.date_create})\n````\n'
            return_history_text += message_object.user_message
            return_history_text += '\n````\n\n'
            return_history_text += f'## ASSISTANT AI ({message_object.date_create})\n````\n'
            return_history_text += message_object.llm_response
            return_history_text += '\n````\n\n'
    else:
        # ヒストリーに含める会話数が0の場合
        return_history_list = None
        return_history_text = ''
    return async_to_sync(channel_layer.group_send)(room_group_name, {
                            'type':     'complete_task_get_history',
                            'response': {
                                'status':       'success',
                                'history_list': return_history_list,
                                'history_text': return_history_text,
                                'data_dict':    data_dict,
                            },
                        })

@shared_task(max_retries                = 1,     # リトライ回数
             task_acks_late             = True,  # Task 終了後に Ask する
             task_reject_on_worker_lost = False, # Worker 異常終了時に再実行する
             visibility_timeout         = 360,   # Ack されない Task の再スケジューリング(sec)
             worker_prefetch_multiplier = 1,     # Task のプリフェッチ数(default:4)
             )
def save_message_models(room_group_name:str,
                        room_id:str,
                        data_dict:dict,):
    channel_layer = get_channel_layer()
    
    user_settings = {k: v for k, v in data_dict.items()\
                            if (k.lower() != 'user_sentence' and\
                                k.lower() != 'llm_response' and\
                                k.lower() != 'tokens_info_dict' and\
                                k.lower() != 'history_list')}

    Message.objects.create(
            room_id                        = Room.objects.get(room_id=room_id),
            message_id                     = data_dict['message_id'],
            user_message                   = data_dict['user_sentence'],
            llm_response                   = text_modify_fnc(data_dict['llm_response']),
            user_settings                  = user_settings,
            tokens_info_dict               = data_dict['tokens_info_dict'],
            history_list                   = data_dict['history_list'],)

    return async_to_sync(channel_layer.group_send)(room_group_name, {
                            'type':     'complete_task_save_message_models',
                            'response': {
                                'status': 'success',
                            },
                        })

@shared_task(max_retries                = 1,     # リトライ回数
             task_acks_late             = True,  # Task 終了後に Ask する
             task_reject_on_worker_lost = False, # Worker 異常終了時に再実行する
             visibility_timeout         = 360,   # Ack されない Task の再スケジューリング(sec)
             worker_prefetch_multiplier = 1,     # Task のプリフェッチ数(default:4)
             )
def replace_default_room_name(room_group_name:str,
                              room_id:str,
                              user_sentence:str = DEFAULT_ROOM_NAME,
                              ) -> None:
    channel_layer = get_channel_layer()
    
    # room_name がデフォルトの場合には最初の質問を room_name に設定する
    room                       = Room.objects.get(room_id=room_id)
    room_settings_model_object = RoomSettings.objects.get(room_id=room)
    
    if room_settings_model_object.room_name == DEFAULT_ROOM_NAME:
        if len(user_sentence) > MAX_LEN_ROOM_NAME:
            room_name = user_sentence[:MAX_LEN_ROOM_NAME-4] + '...'
        room_settings_model_object.room_name = room_name
        room_settings_model_object.save()

    return async_to_sync(channel_layer.group_send)(room_group_name, {
                            'type':     'complete_task_replace_default_room_name',
                            'response': {
                                'status': 'success',
                            },
                        })