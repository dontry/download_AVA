'''
Created on 2013-12-24

@author: Wangweining
'''
#coding:utf-8

import threading
import re
import urllib2
import logging
import time

portdicts ={'v':"3",'m':"4",'a':"2",'l':"9",'q':"0",'b':"5",'i':"7",'w':"6",'r':"8",'c':"1"}
targets = []
for i in xrange(1,3):
        target = r"http://www.cnproxy.com/proxy%d.html" % i
        targets.append(target)
        
#grab proxy with matching rex
p = re.compile(r'''<tr><td>(.+?)<SCRIPT type=text/javascript>document.write\(":"\+(.+?)\)</SCRIPT></td><td>(.+?)</td><td>.+?</td><td>(.+?)</td></tr>''')
rawProxyList = []
checkedProxyList = []

class ProxyGet(threading.Thread):
    '''
    classdocs
    '''


    def __init__(self, target, log):
        '''
        Constructor
        '''
        threading.Thread.__init__(self)
        self.target = target
        self.log = log
        global rawProxyList
        #self.proxyList = []
    
    def getProxy(self):
        print "target website of proxy server: " + self.target
        req = urllib2.urlopen(self.target)
        response = req.read()
        #print chardet.detect(response)
        matches = p.findall(response)
          
        for row in matches:
            ip = row[0]
            port = row[1]
            port = map(lambda x:portdicts[x], port.split('+'));#convert the port alphabet to digits
            port = ''.join(port)
            agent = row[2]
            addr = row[3].decode("cp936").encode("utf-8")
            proxy = [ip,port,addr]
            rawProxyList.append(proxy)

    def run(self):
        self.getProxy()
      
class ProxyCheck(threading.Thread):
    def __init__(self, proxyList, log):
        threading.Thread.__init__(self)
        self.proxyList = proxyList
        self.timeout = 10
        self.testUrl = "http://www.dpchallenge.com/"
        self.testStr = "DPChallenge"
        self.log = log
        global checkedProxyList
        #self.checkedProxyList = []
        
    def checkProxy(self):
        #checkedProxyList =[]
        cookies = urllib2.HTTPCookieProcessor()
        
        for proxy in self.proxyList:
            proxyHandler = urllib2.ProxyHandler({"http" : r'http://%s:%s' %(proxy[0], proxy[1])})
            opener = urllib2.build_opener(cookies, proxyHandler)
            opener.addheaders =  [('User-agent', 'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:22.0) Gecko/20100101 Firefox/22.0')] 
            self.log.info(r'http://%s:%s' %(proxy[0],proxy[1]))
            t1 = time.time()
            
            try:
                req = opener.open(self.testUrl, timeout = self.timeout)
                self.log.info("urlopen is ok....")
                result = req.read()
                self.log.info("read html....")
                duration = time.time() - t1
                pos = result.find(self.testStr)
                self.log.info("pos is %s" %pos)
                
                if pos > 1:
                    if duration < 12:  # link response less than 12 seconds
                        checkedProxyList.append((proxy[0],proxy[1],proxy[2],duration))
                        status = r"ok ip: %s %s %s %s" %(proxy[0], proxy[1], proxy[2], str(duration))
                        self.log.info(status)
                        print(status)
                else:
                    continue
            except Exception, e:
                print e.message
                continue
    
    def run(self):
        self.checkProxy()