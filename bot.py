from twitter import *
from urllib.error import HTTPError
from datetime import datetime
import time, configparser, re, signal, os

config = configparser.ConfigParser()
config.read('./share/config')

# API キー 設定 
OAUTH_TOKEN = config['API_KEY']['OAUTH_TOKEN']
OAUTH_SECRET = config['API_KEY']['OAUTH_SECRET']
CONSUMER_KEY = config['API_KEY']['CONSUMER_KEY']
CONSUMER_SECRET = config['API_KEY']['CONSUMER_SECRET']

# BOT の設定
INTERVAL = int(config['APP']['INTERVAL'])
MYNAME = "3_way_handshake"

# 最後に返信した tweet の tweet_id を取得
last_mention_id = config['APP']['LAST_MENTION_ID']

status={"SYN-RECEIVED":[], "ESTABLIESHED":[]}
t = Twitter(auth=OAuth(OAUTH_TOKEN, OAUTH_SECRET,
                         CONSUMER_KEY, CONSUMER_SECRET))

def do_main():
    """ 一定間隔でbotを動かす

    config ファイルで設定された INTERVAL に従って、
    一定間隔でbotを動作させる。
    """
    while True:
        bot()
        config.set("APP", "LAST_MENTION_ID", str(last_mention_id))
        with open("./share/config", "w") as f:
            config.write(f)
        time.sleep(INTERVAL)

def bot():
    """ メンションを受け取り、3-way-handshakeする。

    メンションを取得し、内容によって、異なる返答をする。
    """
    print("[DEBUG] {0:s}".format(str(status)))
    status['ESTABLIESHED'] = []
    mentions = get_mentions()
    if mentions is None:
        return 
    for mention in mentions:
        res = create_response(mention)
        print("[LOG]" + res)
        if res is not None:
            try:
                t.statuses.update(status=res)
            except (HTTPError, TwitterHTTPError):
                print("Error")


def get_mentions():
    """ 
    メンションを取得し、screen_nameとtextからなるタプルの配列を返す。
    """
    global last_mention_id
    mentions = t.statuses.mentions_timeline(since_id=last_mention_id)
    if mentions is None or len(mentions) == 0:
        return None
    tuples = []
    for mention in reversed(mentions):
        name_text = mention['user']['screen_name'], mention['text']
        tuples.append(name_text)
    last_mention_id = int(mentions[0]['id'])

    return tuples

def create_response(mention):
    screen_name = mention[0]
    text = mention[1]
    response_tmplate = "@{0:s} {1:s} at " + str(datetime.today())
    response=""
    
    # メンションの内容を解析
    if not is_mention_to_only_myself(text) or screen_name == MYNAME:
        response = None
    elif is_syn(screen_name, text):
        status['SYN-RECEIVED'].append(screen_name)
        response = response_tmplate.format(screen_name, "SYN+ACK")
    elif is_ack(screen_name, text):
        status['SYN-RECEIVED'].remove(screen_name)
        status['ESTABLIESHED'].append(screen_name)
        response = response_tmplate.format(screen_name, "ESTABLIESHED")
    else:
        response = response_tmplate.format(screen_name, "RST")

    return response

def is_mention_to_only_myself(text):
    """
    メンションが自分だけに送られているのか判定する
    """
    p = re.compile("@[a-zA-Z0-9_]+\s*")
    users = p.findall(text) 
    if len(users) == 1:
        return True
    else :
        return False

def is_syn(screen_name, text):
    """
    SYN かどうか確認
    """
    if not is_syn_str(text) or screen_name in status['SYN-RECEIVED']:
        return False
    else:
        return True

def is_syn_str(text):
    """ 
    受信した文字列に"SYN"が含まれるかどうか確認する。
    """
    if text.find("SYN") == -1 or text.find("syn") == -1:
        return False
    else:
        if text.find("ACK") != -1 or text.find("ack") != -1:
            return False
        return True

def is_ack(screen_name, text):
    """
    ACK かどうか確認
    """
    if not is_ack_str(text) or screen_name in status['ESTABLIESHED']:
        return False
    else:
        return True

def is_ack_str(text):
    """ 
    受信した文字列に"ACK"が含まれるかどうか確認する。
    """
    if text.find("ACK") == -1 or text.find("ack") == -1:
        return False
    else:
        if text.find("SYN") != -1 or text.find("syn") != -1:
            return False
        return True

if __name__ == '__main__':
    do_main()
