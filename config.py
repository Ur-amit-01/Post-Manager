import re, os
from os import environ

id_pattern = re.compile(r'^.\d+$') 

API_ID = os.environ.get("API_ID", "22012880")
API_HASH = os.environ.get("API_HASH", "5b0e07f5a96d48b704eb9850d274fe1d")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8113642693:AAG9yJpZjyhKIP_nhsIIoc8ZsiTJ-gsudLU") 
DB_NAME = os.environ.get("DB_NAME","amit")     
DB_URL = os.environ.get("DB_URL","mongodb+srv://uramit0001:EZ1u5bfKYZ52XeGT@cluster0.qnbzn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
ADMIN = [int(admin) if id_pattern.search(admin) else admin for admin in os.environ.get('ADMIN', '2031106491').split()]
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in os.environ.get('ADMINS', '2031106491').split()]
PORT = os.environ.get("PORT", "8080")

ERROR_MESSAGE = bool(os.environ.get('ERROR_MESSAGE', False)) # Set True or False
NEW_REQ_MODE = bool(environ.get('NEW_REQ_MODE', True)) # Set True or False
SESSION_STRING = os.environ.get("SESSION_STRING", "")

START_PIC = os.environ.get("START_PIC", "")
FORCE_PIC = os.environ.get("FORCE_PIC", "https://telegra.ph/file/e292b12890b8b4b9dcbd1.jpg")
AUTH_CHANNEL = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('AUTH_CHANNEL', '-1002385466192').split()] #Ex : ('-10073828 -102782829 -1007282828')
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1002027394591"))

REACTIONS = ["🤝", "😇", "🤗", "😍", "🎅", "🥰", "🤩", "😘", "😛", "😈", "🎉", "🫡", "😎", "🔥", "🤭", "🌚", "🆒", "👻", "😁"] #don't add any emoji because tg not support all emoji reactions

