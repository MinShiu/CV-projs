import cv2
import time
import requests
import datetime
import argparse
import numpy as np
from flask import Flask

from func import *
from person import Person

## constant
TOL = 30
WIDTH = 1080
HEIGHT = 720
AREA_TH = 2000
FONT = cv2.FONT_HERSHEY_SIMPLEX
KERNEL_OP = np.ones((3, 3), np.uint8)
KERNEL_CL = np.ones((17, 17), np.uint8)

## argument parser
parser = argparse.ArgumentParser()
parser.add_argument(
    '-t',
    '--tunnel',
    dest='tunnel',
    type=str,
    default='https://laurettajem.localtunnel.me',
    help='Address of localtunnel')
parser.add_argument(
    '-c',
    '--cap',
    dest='cap',
    type=str,
    default='rtsp://admin:12345@10.0.33.163:554/MediaInput/h264',
    help='Streaming address')
parser.add_argument(
    '-l',
    '--logfile',
    dest='logfile',
    type=str,
    default=r'C:\Users\admin\Desktop\lvl3lby2.txt',
    help='Log file path')
args = parser.parse_args()

## variables
cap, tunnel, logfile = cv2.VideoCapture(args.cap), args.tunnel, args.logfile
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
showCountTimerResetM = time.time()
showCountTimerResetF = time.time()
exceedCountMale = False
exceedCountFemale = False
listening_M = False
listening_F = False
#listening_countTimer = False
#condM = True
#condF = True
ltime = True
ltimeF = True
ltimeM = True

## load log file upon restart and restore counts
with open(logfile, 'r') as f:
    countML, countFL = [int(x.split(':')[-1]) for x in f.readlines()[-1].split(']')[1].replace('\n', '').split(' ')[1:]]

while(cap.isOpened()):

    ## retrieve frame and handle eof
    ret, frame = cap.read()
    if not ret:
        break
    
    # examine current cleaning status of female toilet (perform once every 60 secs)
    if listening_F:
        
        if ltimeF:
            tF = time.time()
            ltimeF = False
        
        if time.time() - tF > 60:
            print('REQUEST: female lby2 do request')
            ltimeF = True
            listening_F = waitForComplete('status_lobby2_female', listening_F, tunnel)
            currentSendCountF = 0
            showCountTimerResetF = time.time()
    else:
        
        ltimeF = True
    
    # examine current cleaning status of male toilet (perform once every 60 secs)
    if listening_M:
        
        if ltimeM:
            tM = time.time()
            ltimeM = False
            
        if time.time() - tM > 60:
            print('REQUEST: male lby2 do request')
            ltimeM = True
            listening_M = waitForComplete('status_lobby2_male', listening_M, tunnel)
            currentSendCountM = 0
            showCountTimerResetM = time.time()
    else:
        
        ltimeM = True
    
    # send incomplete signal
    if performIncompleteAction_M:
        performIncompleteAction_M = incompleteAction(tunnel, 'lby2m')
        
    if performIncompleteAction_F:
        performIncompleteAction_F = incompleteAction(tunnel, 'lby2f')

    ## resizing and apply background subtraction
    frame = cv2.resize(frame, (WIDTH, HEIGHT))
    fgmask2 = fgbg.apply(frame)

    ## use morphology to remove noise on mask
    mask2 = cv2.morphologyEx(fgmask2, cv2.MORPH_OPEN, KERNEL_OP)
    mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, KERNEL_CL)

    ## finding countour base on mask constructed
    contours0, hierarchy = cv2.findContours(mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) #prior to opencv4, 2 arguments are returned (originally 3 of them)

    for cnt in contours0:

        ## filter out object with small area
        area = cv2.contourArea(cnt)
        #print(area)
        if area > AREA_TH :

            ## calculate center of object by moments
            M = cv2.moments(cnt)
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            x,y,w,h = cv2.boundingRect(cnt)
            cv2.circle(frame, (cx, cy), 5, (0,0,255), -1)
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
            if min_dist < 100:
                new = False
                i = nearest_ppl
                i.updateCoords(cx,cy)

                ## going into male toilet
                if i.going_DOWN(500) and cx > 500 and time.time() - t1 > 0.5:
                    t1 = time.time()
                    timer = time.time()
                    countM += 1
                    countML += 1
                    currentSendCountM += 1
                    i.resetTracks()
                    detected(frame, '2', cnt, x, y, w, h, cx, cy, 'M', currentSendCountM)
                    if currentSendCountM >= 2:
                        exceedCountMale = True
                        currentSendCountM = 0
                        listening_M = True
                        performIncompleteAction_M = True
                        print('LISTENER: listeningM now')

                ## going into female toilet
                elif i.going_RIGHT(775) and 180 < cy < 320 and time.time()-t2 > 0.5:
                    t2 = time.time()
                    timer = time.time()
                    countF += 1
                    countFL += 1
                    currentSendCountF += 1
                    i.resetTracks()
                    detected(frame, '2', cnt, x, y, w, h, cx, cy, 'F', currentSendCountF)
                    if currentSendCountF >= 2:
                        exceedCountFemale = True
                        currentSendCountF = 0
                        listening_F = True
                        performIncompleteAction_F = True
                        print('LISTENER: listeningF now')
                        
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
        strML = 'IN_M : ' + str(countML)
        strFL = 'IN_F : ' + str(countFL)
        strCM = 'CurrM : ' + str(currentSendCountM)
        strCF = 'CurrF : ' + str(currentSendCountF)
        strTM = 'MTime : ' + str(round(time.time() - showCountTimerResetM))
        strTF = 'FTime : ' + str(round(time.time() - showCountTimerResetF))
        cv2.putText(frame, strML, (40, 100), FONT,
                    0.5, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, strFL, (40, 130), FONT,
                    0.5, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, strCM, (40, 160), FONT,
                    0.5, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, strCF, (40, 190), FONT,
                    0.5, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, strTM, (40, 220), FONT,
                    0.5, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, strTF, (40, 250), FONT,
                    0.5, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.imshow('Frame', frame)
        #cv2.imshow('FrameR', frameR)
        #cv2.imshow('mask', mask2)
        
    if exceedCountMale:
        showCountTimerResetM = time.time()
        exceedCountMale = False
        
    if exceedCountFemale:
        showCountTimerResetF = time.time()
        exceedCountFemale = False
    
    # if the time exceed 75 mins, send the attention message MALE
    if time.time() - showCountTimerResetM > 4500:
        requests.get(tunnel + '/incomplete/lby2m')
        str_triggered1 = str(currentSendCountM) + 'users at L3 (Lobby2) male toilet \
            last seen 75 mins ago, attention required. '
        doPosReq("Lendlease", "JEM | Washroom Monitoring", str_triggered1, "task", "System Administrator",
                 datetime.datetime.now().strftime(
                     '%H:%M'), datetime.datetime.now().strftime('%Y-%m-%d'),
                 'data:image/jpg;base64,' + jpg_as_text.decode())
        print('TIMER: time exceed 75 mins-MALE')
        listening_M = True
        showCountTimerResetM = time.time()
        
    # if the time exceed 60 mins, send the attention message FEMALE
    if time.time() - showCountTimerResetF > 3600:
        requests.get(tunnel + '/incomplete/lby2f')
        str_triggered2 = str(currentSendCountM) + 'users at L3 (Lobby2) male toilet \
            last seen 60 mins ago, attention required. '
        doPosReq("Lendlease", "JEM | Washroom Monitoring", str_triggered2, "task", "System Administrator",
                 datetime.datetime.now().strftime(
                     '%H:%M'), datetime.datetime.now().strftime('%Y-%m-%d'),
                 'data:image/jpg;base64,' + jpg_as_text.decode())
        print('TIMER: time exceed 60 mins-FEMALE')
        listening_F = True
        showCountTimerResetF = time.time()

    ## write counts into logfile every 30 mins
    ctime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if (ctime.split(' ')[1].split(':')[1] == '00' or ctime.split(' ')[1].split(':')[1] == '30') and ctime.split(' ')[1].split(':')[2] == '00' and not(writeOnce):
        writeOnce = True
        string = '[' + ctime + '] countM:' + str(countML) + ' countF:' + str(
            countFL) + '\n'
        with open(logfile, 'a') as f:
            f.write(string)
    elif (ctime.split(' ')[1].split(':')[1] == '00' or ctime.split(' ')[1].split(':')[1] == '30') and ctime.split(' ')[1].split(':')[2] == '01':
        writeOnce = False
    
    ## reset total visitor count at midnight
    tn = datetime.datetime.now().time()
    if tn.hour == 0 and tn.minute == 0 and tn.second == 5:
        countML = 0
        countFL = 0

    k = cv2.waitKey(1)
    if k == 27:
        break
        
cap.release()
cv2.destroyAllWindows()
