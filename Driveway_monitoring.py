import cv2
import time
import base64
import datetime
import requests
import numpy as np

def doPosReq(organization, group, title, taskType, user, duetime, duedate, photo):
    """function to perform post request"""
    
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

########################################### Main Script ###########################################

cap = cv2.VideoCapture('rtsp://admin:12345@10.0.33.231:554/MediaInput/h264')

## constants
LOWERB = np.array([50, 50, 50])
UPPERB = np.array([110, 110, 110])
TIMETHRESH = 30.0

## variables
low = 5000
t = time.time()
firstSend = True     # to control only send message once between frames
countBool = False    # to detect how long the jam lasting

while(True):    
    
    ret, frame = cap.read()
    frame_cpy = frame.copy()
    frame_cpy = cv2.resize(frame_cpy, (640,480))
    
    ## small frame for colour detection
    sframe = frame_cpy[260:380, 420:530]
    
    ## create mask to count inrange pixels
    mask = cv2.inRange(sframe, LOWERB, UPPERB)

    print(np.count_nonzero(mask))
    
    ## algorithm: if the color of floor in sframe is different, implies car detected
    if np.count_nonzero(mask) >= 5000:
        t = time.time()
    cv2.putText(frame_cpy, ' Timer : ' + str(round(time.time() - t, 1)) ,(30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA) 
    
    ## if color changes more than 30 secs, jam detected
    if round(time.time() - t, 1) > TIMETHRESH:
        countBool = True
        maxC = round(time.time() - t, 1)
        ctime = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        
        ## record down lowest pixel value, logging purpose
        if np.count_nonzero(mask) < low:
            low = np.count_nonzero(mask)
            
        cv2.imwrite('C:\\Users\\admin\\Desktop\\Image_Driveway\\' + ctime + '.jpg', frame)
        
        ## send message once
        if firstSend:
            rsz = cv2.resize(frame, (200, 200))
            retval, buffer = cv2.imencode('.jpg', rsz)
            jpg_as_text = base64.b64encode(buffer)  
            string = 'Driveway congestion detected.'
            doPosReq("Lendlease", "JEM | Carpark Driveway Monitoring", string, "photo", "System Administrator", 
                     datetime.datetime.now().strftime('%H:%M'), datetime.datetime.now().strftime('%Y-%m-%d'), 
                     'data:image/jpg;base64,' + jpg_as_text.decode())
            firstSend = False
            
    ## jam resolved, roll back state of variables and save to log file
    elif (round(time.time() - t, 1) < timeThreshold) and countBool:
        countBool = False
        string = ctime + ',' + str(maxC) + ',' + str(low) + '\n'
        low = 5000
        firstSend = True
        with open(r'C:\Users\admin\Desktop\log_driveway.txt', 'a') as f:
            f.write(string)       

    if cv2.waitKey(30) == 27:
        break
    cv2.imshow('mask', mask)
    cv2.imshow('large frame', frame_cpy)
    cv2.imshow('small frame', sframe)
    
cap.release()
cv2.destroyAllWindows()
