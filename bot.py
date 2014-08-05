
from twitter import *
from urllib.error import HTTPError
import time, configparser, re, signal, os

config = configparser.ConfigParser()
config.read('./config')

OAUTH_TOKEN = config['API_KEY']['OAUTH_TOKEN']
OAUTH_SECRET = config['API_KEY']['OAUTH_SECRET']
CONSUMER_KEY = config['API_KEY']['CONSUMER_KEY']
CONSUMER_SECRET = config['API_KEY']['CONSUMER_SECRET']

INTERVAL = int(config['APP']['INTERVAL'])
MYNAME = "3_way_handshake"

t = Twitter(auth=OAuth(OAUTH_TOKEN, OAUTH_SECRET,
                         CONSUMER_KEY, CONSUMER_SECRET))

# 最後に返信したtweetのtweet_idを代入
if os.path.exists("./last_mention_id"):
    with open("./last_mention_id", "r") as f:
        last_mention_id = int(f.readline())
else :
    last_mention_id = 1 

status={"SYN-RECEIVED":[], "ESTABLIESHED":[]}

def do_main():
    """ 一定間隔でbotを動かす

    config ファイルで設定された INTERVAL に従って、
    一定間隔でbotを動作させる。
    """
    while True:
        bot()
        time.sleep(INTERVAL)

def bot():
    """ メンションを受け取り、3-way-handshakeする。

    メンションを取得し、内容によって、異なる返答をする。
    """
    print("[DEBUG]")
    print(status)
    status['ESTABLIESHED'] = []
    mentions = get_mentions()
    if mentions is None:
        return 
    for mention in mentions:
        res = create_response(mention)
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
    response = ""
    
    # メンションの内容を解析
    if not is_mention_to_only_myself(text) or screen_name == MYNAME:
        response = None
    elif is_syn(screen_name, text):
        status['SYN-RECEIVED'].append(screen_name)
        response = "@" + screen_name + " SYN+ACK"
    elif is_ack(screen_name, text):
        status['SYN-RECEIVED'].remove(screen_name)
        status['ESTABLIESHED'].append(screen_name)
        response = "@" + screen_name + " ESTABLISHED"
    else:
        response = "@" + screen_name + " RST"

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

def handler(signum, frame):
    """
    SIGINT を受け取った時に、last_mention_idをファイルに出力
    """
    with open('./last_mention_id', 'w') as f:
        f.write(str(last_mention_id)) 

if __name__ == '__main__':
    #シグナル設定
    signal.signal(signal.SIGINT, handler)
    do_main()
