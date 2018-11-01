import cv2
import time
import base64
import requests
import datetime
import numpy as np

## constant
TOL = 30
WIDTH = 1080
HEIGHT = 720
AREA_TH = 1400
FONT = cv2.FONT_HERSHEY_SIMPLEX
KERNEL_OP = np.ones((3,3), np.uint8)
KERNEL_CL = np.ones((21,21), np.uint8)

## load and resize an exclamation mark image, to be used when sending message
img = cv2.imread(r'C:\Users\admin\Pictures\attention.png')
img = cv2.resize(img, (200,200))
retval, buffer = cv2.imencode('.png', img)
jpg_as_text = base64.b64encode(buffer)

############################################ Class definition ######################################################

class Person:
    def __init__(self, i, xi, yi):
        self.i = i
        self.x = xi
        self.y = yi
        self.tracks = []

    def getTracks(self):
        return self.tracks

    def getId(self):
        return self.i

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def updateCoords(self, xn, yn):
        self.tracks.append([self.x,self.y])
        self.x = xn
        self.y = yn

    def resetTracks(self):
        self.tracks = []

    def going_UP(self, line_up):
        return (len(self.tracks) >= 2 and self.tracks[-1][1] <= line_up and self.tracks[-2][1] >= line_up)

    def going_DOWN(self, line_down):
        return (len(self.tracks) >= 2 and self.tracks[-1][1] >= line_down and self.tracks[-2][1] <= line_down)

    def going_RIGHT(self, line_right):
        return (len(self.tracks) >= 2 and self.tracks[-1][0] >= line_right and self.tracks[-2][0] <= line_right)

    def going_LEFT(self, line_left):
        return (len(self.tracks) >= 2 and self.tracks[-1][0] <= line_left and self.tracks[-2][0] >= line_left)

########################################## Function Definition #####################################################

def handleBoundaries(val, maxval):
    """function to handle boundary values to crop image properly"""
    return 0 if val < 0 else int(maxval) if val > maxval else val

def detected(frame, frame_cpy, cnt, x, y, w, h, cx, cy, sex, currentSendCount):
    """action to perform when someone cross the line"""

    ## handle boundaries
    y1, y2, x1, x2 = handleBoundaries(y-TOL, HEIGHT), handleBoundaries(y+h+TOL, HEIGHT), handleBoundaries(x-TOL, WIDTH), handleBoundaries(x+w+TOL, WIDTH)
    ## save cropped image to local storage
    rsz = frame_cpy[y1:y2, x1:x2]
    timenow = datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S.%f')
    cv2.imwrite('C:\\Users\\admin\\Desktop\\Image_Toilet_Basement\\' + timenow + '.jpg', rsz)

    ## visualization
    cv2.circle(frame, (cx, cy), 5, (0,0,255), -1)
    cv2.drawContours(frame, cnt, -1, (0,255,0), 3)

    ## push notification to app if more than 70 visitors detected
    if currentSendCount >= 70:
        sex = 'female' if sex == 'F' else 'male'
        str_triggered = str(currentSendCount) + " users at L5 " + sex + " toilet since last seen, attention required."
        doPosReq("Lendlease", "JEM | Washroom Monitoring", str_triggered, "photo", "System Administrator",
                 datetime.datetime.now().strftime('%H:%M'), datetime.datetime.now().strftime('%Y-%m-%d'),
                 'data:image/jpg;base64,' + jpg_as_text.decode())

def doPosReq(organization, group, title, taskType, user, duetime, duedate, photo):
    """perform post requests to app api"""

    print(title)

    ## define json object and send message
    json_dict = {
        "organization" : organization,
        "group" : group,
        "title" : title,
        "taskType" : taskType,
        "user" : user,
        "duetime" : duetime,
        "duedate" : duedate,
        "photo" : photo
    }
    r = requests.post('http://app.lauretta.io/api/task/upload', data=json_dict)
    print(f'Status code for request sent to {user}: {r.status_code}')

############################################### Main ##############################################################

cap = cv2.VideoCapture('rtsp://admin:12345@10.0.33.197:554/MediaInput/h264')
## demonstrative line (currently not in used)
pt1 =  [338, 270]
pt2 =  [388, 210]
pts_L1 = np.array([pt1 ,pt2], np.int32)
pts_L1 = pts_L1.reshape((-1,1,2))

pt3 =  [371, 570]
pt4 =  [970, 570]
pts_L2 = np.array([pt3 ,pt4], np.int32)
pts_L2 = pts_L2.reshape((-1,1,2))

## variables
fgbg = cv2.createBackgroundSubtractorKNN(history=600, dist2Threshold=700, detectShadows=False)
wd = cap.get(3)    # getting width of cap
hg = cap.get(4)    # getting height of cap
persons = []
countM = 0    # current count in female toilet
countML = 0    # total female visitors
countF = 0    # current count in male toilet
countFL = 0    # total male visitors
pid = 1
t1 = 0    # timer to control gap between every detection
t2 = 0
timer = time.time()    # timer to control if the toilet is idle for too long
writeOnce = False
currentSendCountM = 0    # variable to track count number for pushing notification
currentSendCountF = 0
start = time.time()
exceedCountMale = False
exceedCountFemale = False
elapsed = 0

## load log file upon restart and restore counts
with open(r'C:\Users\admin\Desktop\log_toilet2.txt', 'r') as f:
    counta, countb, countaL, countbL = [int(x.split(':')[-1]) for x in f.readlines()[-1].split(']')[1].replace('\n', '').split(' ')[1:]]

while(cap.isOpened()):

    ## retrieve frame and handle eof
    ret, frame = cap.read()
    if not ret:
        break

    ## resizing and apply background subtraction
    frame = cv2.resize(frame, (WIDTH, HEIGHT))
    frame_cpy = frame.copy()
    fgmask2 = fgbg.apply(frame)

    ## use morphology to remove noise on mask
    mask2 = cv2.morphologyEx(fgmask2, cv2.MORPH_OPEN, KERNEL_OP)
    mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, KERNEL_CL)

    ## finding countour base on mask constructed
    _, contours0, hierarchy = cv2.findContours(mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours0:

        ## filter out object with small area
        area = cv2.contourArea(cnt)
        if area > AREA_TH :

            ## calculate center of object by moments
            M = cv2.moments(cnt)
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            x,y,w,h = cv2.boundingRect(cnt)
            new = True

            min_dist = 1000

            ## loop through person in persons list, and bind current countour with
            ## nearest person
            for i in persons:
                dist_coord = (abs(cx-i.getX()), abs(cy-i.getY()))
                dist = sum(dist_coord)
                if dist < min_dist:
                    min_dist = dist
                    nearest_ppl = i

            ## detection (detection could only happened once every 0.75 sec)
            if min_dist < 60:
                new = False
                i = nearest_ppl
                i.updateCoords(cx,cy)

                ## going into male toilet
                if i.going_LEFT(160) and cy > 300 and time.time() - t1 > 1:
                    t1 = time.time()
                    timer = time.time()
                    countM += 1
                    countML += 1
                    currentSendCountM += 1
                    i.resetTracks()
                    detected(frame, frame_cpy, cnt, x, y, w, h, cx, cy, 'M', currentSendCountM)
                    # after the notification is pushed, reset count for next attempt
                    if currentSendCountM >= 70:
                        exceedCountMale = True
                        currentSendCountM = 0

                ## going out from male toilet
                elif i.going_RIGHT(160) and cy > 300 and time.time()-t1 > 1:
                    t1 = time.time()
                    timer = time.time()
                    ## current count cant be less than 0
                    if countM > 0:
                        countM -= 1
                    i.resetTracks()
                    detected(frame, frame_cpy, cnt, x, y, w, h, cx, cy, 'M', currentSendCountM)

                ## going out from female toilet
                elif i.going_LEFT(390) and cy < 225 and time.time()-t2 > 1:
                    t2 = time.time()
                    timer = time.time()
                    if countF > 0:
                        countF -= 1
                    i.resetTracks()
                    detected(frame, frame_cpy, cnt, x, y, w, h, cx, cy, 'F', currentSendCountF)

                ## going into female toilet
                elif i.going_RIGHT(390) and cy < 225 and time.time()-t2 > 1:
                    t2 = time.time()
                    timer = time.time()
                    countF += 1
                    countFL += 1
                    currentSendCountF += 1
                    i.resetTracks()
                    detected(frame, frame_cpy, cnt, x, y, w, h, cx, cy, 'F', currentSendCountF)
                    if currentSendCountF >= 70:
                        exceedCountFemale = True
                        currentSendCountF = 0

            ## restrict tracks
            for pe in persons:
                if len(pe.getTracks()) > 200:
                    pe.resetTracks()

            ## create new person if current contour is too far from the
            ## last detected coordinate of every person in persons list
            if new:
                p = Person(pid, cx, cy)
                persons.append(p)
                pid += 1

            ## restrict person number
            if len(persons) > 10:
                persons.remove(persons[0])

        ## text to show on frame
        str_M = 'COUNT M : '+ str(countM)
        str_F = 'COUNT F : ' + str(countF)
        strML = 'IN_M : ' + str(countML)
        strFL = 'IN_F : ' + str(countFL)
        #cv2.putText(frame, str_a ,(40,140), FONT, 0.5, (0,0,255), 1, cv2.LINE_AA)
        #cv2.putText(frame, str_b ,(40,170), FONT, 0.5, (0,0,255), 1, cv2.LINE_AA)
        cv2.putText(frame, strML ,(40,140), FONT, 0.5, (0,0,255), 1, cv2.LINE_AA)
        cv2.putText(frame, strFL ,(40,170), FONT, 0.5, (0,0,255), 1, cv2.LINE_AA)
        cv2.imshow('Frame', frame)

    if exceedCountMale and exceedCountFemale:
    	start = time.time()
    	exceedCountMale = False
    	exceedCountFemale = False

    ## if the time exceed 75 mins, send the attention message
    if time.time() - showCountTimerReset > 4500:
        str_triggered = str(currentSendCountM) + ' male and ' + str(currentSendCountF) + ' female visit toilet at l5-lobby2.'
        img = cv2.imread(r'C:\Users\admin\Pictures\attention.png')
        img = cv2.resize(img, (200,200))
        retval, buffer = cv2.imencode('.png', img)
        jpg_as_text = base64.b64encode(buffer)
        doPosReq("Lendlease", "JEM | Washroom Monitoring", str_triggered, "photo", "System Administrator",
             datetime.datetime.now().strftime('%H:%M'), datetime.datetime.now().strftime('%Y-%m-%d'),
             'data:image/jpg;base64,' + jpg_as_text.decode())
        currentSendCountM = 0
        currentSendCountF = 0
        exceedThreshF = False
        exceedThreshM = False
        showCountTimerReset = time.time()

    ## if idle for too long, reset current count number to 0
    if time.time() - timer > 1800:
        counta = 0
        countb = 0
        timer = time.time()

    ## write counts into logfile every 30 mins
    ctime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if (ctime.split(' ')[1].split(':')[1] == '00' or ctime.split(' ')[1].split(':')[1] == '30') and ctime.split(' ')[1].split(':')[2] == '00' and not(writeOnce):
        writeOnce = True
        string = '[' + ctime + '] countM:' + str(countM) + ' countF:' + str(countF) + ' InM:' + str(countML) + ' InF:' + str(countFL) + '\n'
        with open(r'C:\Users\admin\Desktop\log_toilet2.txt', 'a') as f:
            f.write(string)
    elif (ctime.split(' ')[1].split(':')[1] == '00' or ctime.split(' ')[1].split(':')[1] == '30') and ctime.split(' ')[1].split(':')[2] == '01':
        writeOnce = False

    ## reset total visitor count at midnight
    if datetime.datetime.now().time().hour == 0 and datetime.datetime.now().time().minute == 0 and datetime.datetime.now().time().second == 5:
        countaL = 0
        countbL = 0

    k = cv2.waitKey(30)
    if k == 27:
        break

cap.release()
cv2.destroyAllWindows()
