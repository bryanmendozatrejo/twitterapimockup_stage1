import hug
import sqlite_utils
import configparser
import logging.config
import datetime
import requests
import sqlite3
import base64
import http.client
import json
# import urlib.request
from requests.auth import HTTPBasicAuth

config = configparser.ConfigParser()
config.read('./etc/api.ini')
logging.config.fileConfig(config["logging"]["config"], disable_existing_loggers=False)

@hug.directive()
def sqlite(section="sqlite", key="dbfile1", **kwargs):
    dbfile1 = config[section][key]
    return sqlite_utils.Database(dbfile1)

@hug.directive()
def log(name=__name__, **kwargs):
    return logging.getLogger(name)

globUser = ''

def exists(username, password):
    global globUser
    r = requests.get(f'http://localhost:5000/users/verify?username={username}&password={password}')
    if r.status_code == 200:
        globUser = username
        return True
    else:
        globUser = ''
        return False

@hug.post("/posts/new/", status=hug.falcon.HTTP_201, requires=hug.authentication.basic(exists))
def addPost(
    response,
    message : hug.types.text,
    db: sqlite,
):
    username = globUser
    posts = db["posts"]

    post = {
        "username" : username,
        "message": message,
        "timestamp":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "repost": '',
    }

    try:
        posts.insert(post)
        post["id"] = posts.last_pk
        return post

    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}

@hug.get("/repost/", status=hug.falcon.HTTP_201, requires=hug.authentication.basic(exists))
@hug.post("/repost/", status=hug.falcon.HTTP_201, requires=hug.authentication.basic(exists))
def rePost(
    response, request,
    id: hug.types.number,
    db: sqlite,
):
    username = globUser
    posts = db["posts"]
    posts_db = sqlite3.connect('./var/posts.db')
    c = posts_db.cursor()
    c.execute('SELECT message FROM posts WHERE id=? ', (id,))
    user_post = c.fetchone()
    post = {
        "username" : username,
        "message": user_post[0],
        "timestamp":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "repost": 'http://localhost/allposts' + f'?id={id}'
    }

    try:
        posts.insert(post)
        post["id"] = posts.last_pk
        return post

    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}

@hug.get('/allposts/', status=hug.falcon.HTTP_201)
def getPublicTimeline(request, db: sqlite):
    posts = db["posts"]
    values = []

    try:
        if "id" in request.params:
            values.append(request.params['id'])
            return {"posts": posts.rows_where("id = ?", request.params['id'], order_by= 'timestamp desc')}
        else:
            return {"posts": posts.rows_where(order_by= 'timestamp desc')}

    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
        return {"error": str(e)}

@hug.get("/posts/{username}", status=hug.falcon.HTTP_201)
def getUserTimeline(
    username: hug.types.text,
    response,
    db: sqlite,
):
    posts = db["posts"]
    values = []

    try:
        values.append(username)
        return {"posts": posts.rows_where("username = ?", values, order_by= 'timestamp desc')}
    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
        return {"error": str(e)}

@hug.get("/posts/home/", requires=hug.authentication.basic(exists))
def getHomeTimeline(response, db: sqlite):
    username = globUser
    posts = db["posts"]
    values = []
    data = requests.get(f'http://localhost:5000/followers?username={username}').json()
    print(data)
    # print(data["followers"][0]["friend_username"])
    dataSize = len(data["followers"])

    for i in range(dataSize):
        values.append(data["followers"][i]["friend_username"])

    print("values: ", values)
    if dataSize == 1:
        return {"posts": posts.rows_where("username = ?", values, order_by= 'timestamp desc')}
    elif dataSize > 1:
        post = []
        for val in values:
            temp = []
            temp.append(val)
            post.append(posts.rows_where("username = ?", temp, order_by= 'timestamp desc'))
        return {"posts": post}
    else:
        response.status = hug.falcon.HTTP_401
        return {"error: No followers"}
