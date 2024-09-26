from django.conf import settings
from config.read_env import read_env

# LOAD SECRET STEEINGS
env = read_env(settings.BASE_DIR)

AZURE_SPEECH_SERVICE_API_KEY  = env.get_value('AZURE_SPEECH_SERVICE_API_KEY',str)
AZURE_SPEECH_SERVICE_REGION   = env.get_value('AZURE_SPEECH_SERVICE_REGION',str)
AZURE_SPEECH_SERVICE_LANGUAGE = env.get_value('AZURE_SPEECH_SERVICE_LANGUAGE',str)