'''
Created on 2013-12-21

@author: DonCai
'''
#coding:utf-8
import threading
import Queue
from urllib2 import  Request, urlopen, URLError, HTTPError
import urllib2
import urllib
import time
import re
import os
import socket
import logging
import random
import myProxy
import myUtils

USE_PROXY = False

#imgIdx_file = 'family.txt'
_urlStr = "http://www.dpchallenge.com/image.php?IMAGE_ID="
#dwnDir = "D:\\Pictures\\AVA"
#chkDir = dwnDir + "\\check_point.txt"
matchRex = """<img\ssrc="(http.*?jpg)".*?alt=.*?>"""
nThreads = 5
targets = []

#=============initialize===========
#use proxy?
while True:
    input = raw_input("Do you want to use proxy?(Y/N)")
    if bool(re.search('Y',input, re.IGNORECASE)):
        USE_PROXY = True
        numTarget = raw_input("How many proxy websites do you want to crawl?(Min 2, Max 9)")
        for i in xrange(1, int(numTarget)):
            target = r"http://www.cnproxy.com/proxy%d.html" % i
            targets.append(target)
        break
    if bool(re.search('N', input, re.IGNORECASE)):
        USE_PROXY = False
        break

#initialize download directory
dwnDir = raw_input("Please input the directory you want to store your image: ")
if not os.path.exists(dwnDir):
    os.mkdir(dwnDir)
   
#initialize checkpoint file
chkPoint_filename =  dwnDir + "/check_point.txt" 
if not os.path.isfile(chkPoint_filename):
    f_check = open(chkPoint_filename,'w')
    f_check.close()
   
#initialize image index file
imgIdx_filename = ''
while not os.path.isfile(imgIdx_filename):
    imgIdx_filename = raw_input("Please input the directory of your image index file: ")
 

queue = Queue.Queue()
out_queue = Queue.Queue()
mutex = threading.Lock()
download_timeout = 1200
#socket.setdefaulttimeout(timeout)  

logging.basicConfig(filename = os.path.join(dwnDir,'log_AVA.txt'), level = logging.DEBUG, 
                    filemode ='w', format ='%(asctime)s - %(levelname)s: %(message)s')
log = logging.getLogger('log')

def reporthook(blocks_read, block_size, total_size):
        if not blocks_read:
            print('Connection opened')
        if total_size < 0:
            print('Read %d blocks' % blocks_read)
        else:
            print('downloading: %d KB, totalsize: %d KB' %( blocks_read*block_size/1024.0,total_size/1024.0))



class myThreads(object):
    def __init__(self):
        self.threads = []
    
    def append(self, thread):
        self.threads.append(thread)
    
    def start(self):
        for thread_obj in self.threads:
            thread_obj.start()
       
        for thread_obj in self.threads:
            thread_obj.join()
 
        

class ThreadUrl(threading.Thread):
    #Threaded URL Grab
    def __init__(self, queue, out_queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.out_queue = out_queue
        self.timeout = 180
        self.sleep_download_time = 3
        
    def loadPage(self, host):
        try:
            return urllib.urlopen(host).read()
            log.debug('.'*10+'loading page'+'.'*10)
            print('.'*10+'loading page'+'.'*10)
        except HTTPError, e:
            print ('loading page-----The server couldn\'t fulfill the request.')   
            print 'Error code: ', e.code
            log.error('%s',e.code)
        except URLError, e:
            print ('loading page-----We failed to reach a server.')
            print ('Reason:', e.reason)
            log.error('%s',e.reason)
        
        
    
    def loadPage_proxy(self, host, proxy):
        cookies = urllib2.HTTPCookieProcessor()
        proxyHandler = urllib2.ProxyHandler({"http" : r'http://%s:%s' %(proxy[0], proxy[1])})
        opener = urllib2.build_opener(cookies, proxyHandler)
        urllib2.install_opener(opener)
        response = ''
        try:
            req =  opener.open(host, timeout=self.timeout)
            response = req.read()
            log.debug('.'*10+'loading page'+'.'*10)  
            req.close()                                   
        except HTTPError, e:
            print('loading page------The server couldn\'t fulfill the request.')    
            print ('Error code: ', e.code)
            log.error('%s, %s, %s', self.name, host, e.code)            
        except socket.timeout as e:
            print ('----socket timeout:', host)   
            log.error('%s %s %s', self.name, host, e.code)           
        except URLError, e:
            print('%s--%s--- loading page-----We failed to reach a server.' %(self.name, host) )
            print ('Reason:', e.reason)
            log.error('%s, %s, %s',self.name, host, e.reason)                         
        finally:             
            return response
            
    
    def run(self):
        while True:
            #grab host from queue
            imgIdx = self.queue.get()
            img_dir = dwnDir + '/' + imgIdx + '.jpg'  
            if os.path.isfile(img_dir):  
                continue
            
            host = _urlStr + imgIdx
            #grabs urls of hosts and then grabs and then grab chunk of webpage            
            #chunk = self.loadPage(host)
            time.sleep(self.sleep_download_time) #set your sleep_download_time
            if USE_PROXY:
                chunk = ''
                while chunk == '':
                    time.sleep(self.sleep_download_time)
                    randomCheckedProxy = random.choice(myProxy.checkedProxyList) #ramdonly pick a proxy
                    chunk = self.loadPage_proxy(host, randomCheckedProxy)
                print('%s loading page-----success %s' %(self.name, host))
                log.debug('%s loading page----success %s' %(self.name, host))
            else:
                chunk = self.loadPage(host)
                print('%s loading page-----success %s' %(self.name, host))
                log.debug('%s loading page----success %s' %(self.name, host))                   
            #place chun into out queue
            self.out_queue.put(chunk)
            log.debug('put chunk #%s into out_queue' %host)
            print('put chunk #%s into out_queue' %host)
            #signal to queue job is done
            self.queue.task_done()
            log.debug('task done')
            
            
class DownloadImgThread(threading.Thread):
    #Threaded Url Grab
    def __init__(self, out_queue, chkDir):
        threading.Thread.__init__(self)
        self.out_queue = out_queue
        self.chkDir = chkDir #checkpoint file
        self.sleep_time = 3
        self.content = ""
        
    
    def dwnImage(self, href, opener, pic_dir, img_name):
        pic_file = open(pic_dir, 'wb')   
        print("open picture website....")
        if USE_PROXY:    
            req_img = opener.open(href, timeout=download_timeout)
        else:
            req_img = urllib2.urlopen(href, timeout=download_timeout)
        meta = req_img.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print("Downloading: %s Bytes: %s" %(href, file_size))
        file_size_dl = 0
        block_sz = 8192
        print "picture reading....."
        progress = 0
        count = 0
        reult = myUtils.FAILURE
        while True:
            buffer = req_img.read(block_sz)  # how to avoid getting stuck here?
            if (not buffer) and progress == 100:
                result = myUtils.SUCCESS
                break
            
            file_size_dl += len(buffer)
            pic_file.write(buffer)
            progress = file_size_dl * 100. / file_size
            status = r"%s %s %10d [%3.2f%%]" %(self.name, img_name, file_size_dl, progress)
            status = status + chr(8)*(int(progress/10))
            count +=  1
            if count >= 100:
                break
            print status
            log.debug(status)
           
        pic_file.close()
        req_img.close()
        return  result

    def getImage(self, chunk):
        global imgSum
        imgSum = 0
        hrefCmp = re.compile(matchRex)
        hrefList = hrefCmp.findall(chunk)
        result = ''
        
        for href in hrefList:
            if href.find("http://") == 0:
                imageUrl = href
                nameCmp = re.compile("""\d+\.\w{3}""")
                imageName = nameCmp.findall(imageUrl)
                print (">>%s Downloading %s" %(self.name, imageUrl))     
                log.debug(">>%s Downloading %s" %(self.name, imageUrl))        
                dwnStartTime = time.time()                          
                #print("open the picture....")
                while result =='':
                        time.sleep(3)  
                        try:                       
                            if USE_PROXY:
                                cookies = urllib2.HTTPCookieProcessor()
                                proxy = random.choice(myProxy.checkedProxyList) #ramdonly pick a proxy
                                proxyHandler = urllib2.ProxyHandler({"http" : r'http://%s:%s' %(proxy[0], proxy[1])})
                                opener = urllib2.build_opener(cookies, proxyHandler)
                                urllib2.install_opener(opener)
                                pic_dir = dwnDir + '/' + imageName[0]     
                                if not os.path.isfile(pic_dir):
                                    print (">>new picture: %s" %pic_dir)                                    
                                    dwn_result = self.dwnImage(href, opener, pic_dir, imageName[0].strip('.jpg'))  
                                else:
                                    print("Image has already existed.")
                                    log.debug("Image has already existed.")
                                    break
                                if dwn_result == myUtils.SUCCESS: #if download success write imageName, otherwise repeat download again
                                    result = imageName[0].strip('.jpg')
                               
                            else:
                                try:
                                    pic_dir = dwnDir + '/' + imageName[0]     
                                    if not os.path.isfile(pic_dir):
                                        print (">>new picture: %s" %pic_dir)                                    
                                        dwn_result = self.dwnImage(href, None, pic_dir, imageName[0].strip('.jpg')) 
                                    else:
                                        print("Image has already exsisted.")
                                        log.debug("Image has already exsisted.")
                                        break
                                    if dwn_result == myUtils.SUCCESS: #if download success write imageName, otherwise repeat download again   
                                        result = imageName[0].strip('.jpg')
                                except IOError as e:
                                    msg = 'download', href, '/nerror', e
                                    print(msg)
                                    log.debug(msg)
                                    msg = 'Done:%s /nCopy to: %s' %(href, pic_dir)
                                    print(msg)
                                    log.debug(msg)
                        except HTTPError, e:
                            print('Open image-----------The server couldn\'t open the image.')
                            print ('Error code:', e.code)
                        except socket.timeout as e:
                            print('Open image---------socket timeout for opening image:', imageUrl)
                        except URLError, e:
                            print('Open image---------We failed to reach a server.')
                            print('Reason:', e.reason)
                       
                      	               
       	        dwnEndTime = time.time()
                imgSum += 1
                print ("%s OK for using %f seconds\n" %(imageUrl, dwnEndTime - dwnStartTime))
            else:
                continue
        return result
    
    def DwnImage_checkPoint(self, chunk, sleep_time):
        #if mutex.acquire(1):
        fd = open(imgIdx_filename,'r')
        myUtils.GoCheckPoint(fd, chkPoint_filename)
        f_check = open(chkPoint_filename, 'a')
        
        try:
            time.sleep(sleep_time)
            content = self.getImage(chunk)
            f_check.write(content+'\n') #put content into file after downloading
            print("write into file %s" %chkPoint_filename)
            log.debug("write into file %s" %chkPoint_filename)
            f_check.flush() #flush cache into drive
            
        except:
            #raise Exception()
            return myUtils.FAILURE        
        finally:
            fd.close()
            f_check.close()
        #mutex.release()
        print('Tread %s downloading %s is done.....' %(self.name, self.content))
        return myUtils.SUCCESS
                 
    def run(self):
        while True:
            #global chunk
            #time.sleep(self.sleep_time)     
           # if mutex.acquire(1):   
            chunk = self.out_queue.get()
            ret_val = myUtils.FAILURE
            sleep_time = self.sleep_time
            while ret_val == myUtils.FAILURE:
                ret_val = self.DwnImage_checkPoint(chunk, sleep_time)
                sleep_time += 5 
            print(self.name + ' finish downloading')
            self.out_queue.task_done()
            




#-----------------------------------------
#=============Main Program================
#-----------------------------------------
if __name__ ==  "__main__":

    #Get image names    
    f = file(imgIdx_filename,'r')
    add_List = []

    for idx in f:
        tmp = [idx]
        add_List.extend(tmp)
        
    f.close()
    
    count=0
    list_len=len(add_List)
    while(count<list_len):
        add_List[count]=add_List[count].strip('\n')
        count=count+1
        


    if USE_PROXY:
        #init a thread to get proxy
            getThreads = []
            checkThreads = []
            for i in range(len(targets)):
                t = myProxy.ProxyGet(targets[i], log)
                getThreads.append(t)
            
            for i in range(len(getThreads)):
                getThreads[i].start()
                
            for i in range(len(getThreads)):
                getThreads[i].join()
            
            
            print '.'*10+"total of %s proxy" %len(myProxy.rawProxyList) +'.'*10
            log.info('.'*10+"total of %s proxy" %len(myProxy.rawProxyList) +'.'*10)
               
        #checked proxy
            for i in range(20):
                t = myProxy.ProxyCheck(myProxy.rawProxyList[((len(myProxy.rawProxyList)+19)/20) * i:((len(myProxy.rawProxyList)+19)/20) * (i+1)],log)
                checkThreads.append(t)
            
            for i in range(len(checkThreads)):
                checkThreads[i].start()
            
            for i in range(len(checkThreads)):
                checkThreads[i].join()
                
            print '.'*10+"total of %s proxy pass the examination" %len(myProxy.checkedProxyList) +'.'*10
            log.info('.'*10+"total of %s proxy pass the examination" %len(myProxy.checkedProxyList) +'.'*10)
             
    
#Download images
    #spawn a pool of threads, and pass them queue instances
    for i in range(nThreads):      
        t = ThreadUrl(queue, out_queue)
        t.setDaemon(True)
        t.start()
    
    #populate queue with data
    for imgIdx in add_List:
        #imgURL = _urlStr + add
        chkDir = dwnDir + '/' + imgIdx + '.jpg'
        if not os.path.isfile(chkDir):
            queue.put(imgIdx)
        
    for i in range(nThreads):
        dwn = DownloadImgThread(out_queue, chkDir)
        dwn.setDaemon(True)
        dwn.start()
        
    queue.join()
    out_queue.join()
