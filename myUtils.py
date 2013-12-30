'''
Created on 2013-12-25

@author: Wangweining
'''
import os

SUCCESS = 1
FAILURE = 0

class CheckPointMissContentError:  
    pass 

def GoCheckPoint(fd, checkPoint):
    if not os.path.isfile(checkPoint):
        f_check = open(checkPoint, 'w')
        f_check.close()
    f_check = open(checkPoint, 'r')
    lines = f_check.readlines()
    if len(lines) > 0:
        checkContent = lines[-1] #find last line
        checkContent = checkContent.strip('/n/r')
        #go to the check point
        while True:
            content = fd.readline()
            if content ==  '': # eof 
                pass
                #raise CheckPointMissContentError
            if content.strip('/n/r') == checkContent:
                break
            
    f_check.close() #close checkpoint