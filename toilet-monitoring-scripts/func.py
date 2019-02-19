import cv2
import json
import base64
import requests
import datetime

## constant
TOL = 30
WIDTH = 1080
HEIGHT = 720

def waitForComplete(loc, listening, tunnel):
    """check if complete signal is received on localtunnel"""
    try:
        r = requests.get(tunnel + '/status')
        if json.loads(r.text)[loc] == 'complete':
            print('LISTENING: completed')
            listening = False
        return listening
    except:
        return True
    

def incompleteAction(tunnel, lby):
    """send incomplete signal to localtunnel"""
    try:
        requests.get(tunnel + '/incomplete/' + lby)
        return False
    except:
        return True


def handleBoundaries(val, maxval):
    """function to handle boundary values to crop image properly"""
    return 0 if val < 0 else int(maxval) if val > maxval else val


def detected(frame, lby, cnt, x, y, w, h, cx, cy, sex, currentSendCount):
    """action to perform when someone cross the line"""
    
    # handle boundaries
    y1, y2, x1, x2 = handleBoundaries(y-TOL, HEIGHT), handleBoundaries(
        y+h+TOL, HEIGHT), handleBoundaries(x-TOL, WIDTH), handleBoundaries(x+w+TOL, WIDTH)
    
    # save cropped image to local storage
    frame_cpy = frame.copy()
    rsz = frame_cpy[y1:y2, x1:x2]
    timenow = datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S.%f')
    cv2.imwrite(
        'C:\\Users\\admin\\Desktop\\Image_Toilet_L3L' + lby + '\\' + timenow + '.jpg', rsz)

    # visualization
    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
    cv2.drawContours(frame, cnt, -1, (0, 255, 0), 3)

    # push notification to app if more than n visitors detected
    thres = 30 if sex == 'F' else 45
    if currentSendCount >= thres:
        sex = 'female' if sex == 'F' else 'male'
        str_triggered = str(currentSendCount) + " users at L3 (Lobby" + lby + ") " + \
            sex + " toilet since last seen, attention required."
        doPosReq("Lendlease", "JEM | Washroom Monitoring", str_triggered, "task", "System Administrator",
                 datetime.datetime.now().strftime(
                     '%H:%M'), datetime.datetime.now().strftime('%Y-%m-%d'))
        print(str_triggered)


def doPosReq(organization, group, title, taskType, user, duetime, duedate):
    """perform post requests to app api"""

    # define json object and send message
    json_dict = {
        "organization": organization,
        "group": group,
        "title": title,
        "taskType": taskType,
        "user": user,
        "duetime": duetime,
        "duedate": duedate,
        "photo": ''
    }
    r = requests.post('http://app.lauretta.io/api/task/upload', data=json_dict)
    print(f'POST: Status code for request sent to {user}: {r.status_code}')
