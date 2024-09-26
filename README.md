# DjangoOpenAIVRMChat
<img width="1080px" src="https://github.com/MITSUHIRO-KURIKI/DjangoOpenAIVRMChat/blob/main/static/templates/pages/home/img/img_fps10.gif" />  

<sup>上記サンプルイメージでは、[フリー素材キャラクター「つくよみちゃん」](https://tyc.rei-yumesaki.net/ "フリー素材キャラクター「つくよみちゃん」") （© Rei Yumesaki）を使用しています。</sup>  

## What is this?
[DjangoOpenAIStreamingChat](https://github.com/MITSUHIRO-KURIKI/DjangoOpenAIStreamingChat/ "DjangoOpenAIStreamingChat")をベースに[OpenAI API](https://openai.com/blog/openai-api "OpenAI API")と音声認識に[Azure Speech Studio](https://azure.microsoft.com/ja-jp/products/ai-services/ai-speech "Azure Speech Studio")を利用したVRMとの会話アプリを学習として作成しました
> [!WARNING]  
> <sup>* 本コードはベータ版で完全ではありません。</sup>  
> <sup>* AZURE_SPEECH_SERVICE_API キーを現在直接Templateへ渡しており、本番環境ではサーバサイドからの呼び出しが必要です。(調査中)</sup>  
> <sup>* 即席のため不要なコードも多く、かなり汚いです。</sup>  

 
## 設置
<sup>[DjangoTemplate](https://github.com/MITSUHIRO-KURIKI/DjangoTemplate/ "DjangoTemplate")との差分のみ表示</sup>

#### static > apps > chat > vrm へダウンロードした3Dモデル(.vrm)を格納します  
3Dモデル(.vrm)はお好きなものをおいてください。モデルサイズ等に応じて、 templates/apps/chat/room/include/vrm_script.html のカメラ位置等を修正ください。  
サンプルイメージに使用したのは[つくよみちゃん公式3Dモデル タイプA](https://tyc.rei-yumesaki.net/material/avatar/3d-a/ "つくよみちゃん公式3Dモデル タイプA")「①通常版（VRM）」です。


#### config > settings.pyでの設定
###### RADISの使用
```
# RADIS(WebSoocket/Celery)
IS_USE_RADIS = True
```

#### .envファイル用意
###### AZURE_SPEECH_SERVICE の設定
```
AZURE_SPEECH_SERVICE_API_KEY='*** YOUR AZURE_SPEECH_SERVICE_API_KEY ***'  
AZURE_SPEECH_SERVICE_REGION='*** YOUR AZURE_SPEECH_SERVICE_REGION ***'  
AZURE_SPEECH_SERVICE_LANGUAGE='*** YOUR AZURE_SPEECH_SERVICE_LANGUAGE ***'
```

###### OpenAI API KEYの設定
```
OPENAI_API_KEY='*** YOUR OPENAI_API_KEY ***'
```

###### Radisの利用
```
RADIS_HOST='*** RADIS HOST ***'  
RADIS_PORT='*** RADIS PORT ***'
```

## 実行
* terminal(0)  
<sup>ここでエラーがでる場合には python=3.9.18 を確認してみてください</sup>
```
$ pip install -r requirements-base.txt
$ ProjectSetupBat
$ python manage.py runserver
```
* terminal(1)  
```
$ RunRedisServer
```
* terminal(2)  
```
$ RunCeleryWorker
```

## 主な実行環境
<sup>詳細は requirements-base.txt をご覧ください</sup>
```
python=3.9.18
Django==4.2.1
channels==4.0.0
celery==5.4.0
```

## Other
本アプリケーションで使われる各種ライブラリのライセンスは改変したものを含めて本ライセンスには含まれません。各種ライブラリの原ライセンスに従って利用してください。

## suppl.
<details><summary>TREE</summary>

```
DjangoOpenAIVRMChat/
├─accounts
│  ├─forms
│  ├─models
│  │  └─receivers
│  └─views
│      └─send_mail
├─apps
│  ├─access_security
│  │  └─models
│  │      └─receivers
│  ├─chat
│  │  ├─models
│  │  │  ├─ajax
│  │  │  ├─ModelNameChoice
│  │  │  └─query_search
│  │  └─Utils
│  ├─inquiry
│  │  ├─models
│  │  │  └─receivers
│  │  └─views
│  └─user_properties
│      ├─models
│      └─views
├─common
│  ├─lib
│  │  ├─axes
│  │  ├─social_core
│  │  └─social_django
│  ├─scripts
│  │  ├─DjangoUtils
│  │  ├─LlmUtils
│  │  └─PythonCodeUtils
│  └─views
├─config
│  ├─acsess_logic
│  ├─admin_protect
│  ├─extra_settings
│  └─security
├─media
│  └─apps
│      ├─chat
│      │  └─ai_icon
│      └─user_profile
│          └─user_icon
├─static
│  ├─apps
│  │  ├─chat
│  │  │  │─ai_icon
│  │  │  │   └─default
│  │  │  └─vrm
│  │  └─user_profile
│  │      └─user_icon
│  │          └─default
│  └─templates
│      ├─apps
│      │  └─chat
│      │      └─css
│      ├─base
│      ├─common
│      │  ├─css
│      │  ├─func
│      │  └─lib
│      ├─meta_image
│      └─pages
│          └─home
├─templates
│  ├─accounts
│  │  ├─AccountDelete
│  │  ├─AccountLock
│  │  ├─EmailChange
│  │  │  └─mail_template
│  │  ├─LogIn
│  │  ├─PasswordChange
│  │  ├─PasswordReset
│  │  │  └─mail_template
│  │  ├─SignUp
│  │  │  └─mail_template
│  │  ├─TokenDelete
│  │  └─UserIdSet
│  ├─apps
│  │  ├─chat
│  │  │  ├─include
│  │  │  └─room
│  │  │      └─include
│  │  │          └─feedback
│  │  ├─inquiry
│  │  │  └─inquiry_form
│  │  │      └─notice_admin_mail_template
│  │  └─user_properties
│  │      ├─asset
│  │      │  └─sidenav
│  │      └─Settings
│  ├─common
│  │  ├─asset
│  │  └─debug
│  └─pages
│      ├─general
│      └─home
└─templatetags
```
</details>
