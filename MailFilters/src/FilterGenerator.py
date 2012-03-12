#!/usr/bin/python

'''
Created on Feb 28, 2011

@author: Alexander Winterwald
'''
import glob
import imaplib, rfc822
import string
from datetime import datetime
import pickle
import os
import ConfigParser
import sys
import bz2 
import base64
import re
from Config import Config
import time

FILTER_FOLDER='_filter'
DOMAIN_FOLDER='domain'
EMAIL_PATTERN='[a-zA-Z0-9_\.\-\+]+@[a-zA-Z0-9_\.\-\+]+$'


class msg: # a file-like object for passing a string to rfc822.Message
    def __init__(self, text):
        self.__lines = string.split(text, '\015\012')
        self.__lines.reverse()
    def readline(self):
        try: return self.__lines.pop() + '\n'
        except: return ''
        
class Filter: #contains list of patterns and folder location

    def __init__(self, location, patterns,domain):
        self.__location=location
        self.__patterns = patterns
        self.__domain=domain
        
    def match(self, email):
        if(self.__domain):
            email='@'+email.partition('@')[2]
        return email in self.__patterns
    def getLocation(self):
        return self.__location
    def getFlags(self):
        return None
    def getPatterns(self):
        return self.__patterns
    
    

class FilterGenerator:
    
    
    def __init__(self,config): 
        self.__imapFolderList=set()
        self.__config=config
        self.__filters=[]
        self.__saveFilters=False

        
    # iterates imap folders and read filters and create imap filter folders
    def __iterateImapFolders(self,imap):
        for folder in self.__imapFolderList:
            if folder.endswith(self.__config.imapDelimiter+FILTER_FOLDER):
                self.__addFilter(imap, folder,False)
            else:
                if folder.endswith(self.__config.imapDelimiter+FILTER_FOLDER+self.__config.imapDelimiter+DOMAIN_FOLDER):
                    self.__addFilter(imap, folder,True)
                else:
                    self.__checkImapFolders(imap, folder)

    # add a new filter to filter list            
    def __addFilter(self,imap,folder,domain):
        if self.__saveFilters:
            emailFolder=folder
        else:
            if domain:
                emailFolder=folder[0:-len(self.__config.imapDelimiter+FILTER_FOLDER+self.__config.imapDelimiter+DOMAIN_FOLDER)]
            else:
                emailFolder=folder[0:-len(self.__config.imapDelimiter+FILTER_FOLDER)]
            #check e-mails
        imap.select(folder)
        data = imap.search(None, '(SINCE 01-Jan-1970)')
        messagesToDelete=[]
        if data[0] == 'OK':
            mIds = string.split(data[1][0])
            patterns=set()
            for mId in mIds:
                try:
                    fromHeader = imap.fetch(mId, '(BODY.PEEK[HEADER.FIELDS (FROM TO)])')
                except:
                    print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Error fetching email:'+repr(mId)
                    continue
                if(fromHeader[0] == 'OK'):
                    try:
                        msgHeaders = rfc822.Message(msg(fromHeader[1][0][1]), 0)
                    except:
                        print 'Error reading message '+str(fromHeader)
                        continue
                    if not re.match(EMAIL_PATTERN, msgHeaders.getaddr('from')[1],re.I):
                        print 'bad e-mail '+msgHeaders.getaddr('from')[1]+' in filter folder '+folder
                        continue
                    if domain and not self.__saveFilters:
                        pattern='@'+(msgHeaders.getaddr('from')[1]).partition('@')[2]
                    else:
                        pattern=msgHeaders.getaddr('from')[1]
                    patterns.add(pattern)
                    if msgHeaders.getaddr('to')[1]!='FILTER':
                        result = imap.copy(mId, emailFolder)
                        if(result[0] == 'OK'):
                            messagesToDelete.append(mId)
                            message= 'From:'+msgHeaders.getaddr('from')[1]+'\nTo:FILTER'
                            result=imap.append(folder,'\\Seen',None,message)
                            if(result[0] != 'OK'):
                                print  'can\'t create filter message, error:' + repr(result)
                        else:
                            print 'can\'t copy message, error:' + repr(result)
            if(len(patterns)>0):
                self.__filters.append(Filter(emailFolder, patterns,domain))
                for mId in messagesToDelete:
                    result=imap.store(mId, '+FLAGS', '\\Deleted')
                    if(result[0] != 'OK'):
                        print 'can\'t delete messages:'+repr(result)
                if len(messagesToDelete)>0:
                    imap.expunge()
    # check folder structure and add filter folders if necessary    
    def __checkImapFolders(self,imap,folder):
        if not (folder+self.__config.imapDelimiter+FILTER_FOLDER in self.__imapFolderList):
            folder=folder+self.__config.imapDelimiter+FILTER_FOLDER
            ret=imap.create(folder)
            if ret[0]=='OK':
                print 'Folder '+folder+' created'
                folder=folder+self.__config.imapDelimiter+DOMAIN_FOLDER
                ret=imap.create(folder)
                if ret[0]=='OK':
                    print 'Folder '+folder+' created'
                else:
                    print 'error, can\'t create folder'+ folder +' :' + repr(ret)
            else:
                print 'error, can\'t create folder'+ folder +' :' + repr(ret)
    #generate imap folder list                                    
    def __generateImapFolderList(self, imap):
        folders=imap.list()
        if folders[0]== 'OK':
            for folder in folders[1]:
                folderName=string.split(folder,'"')[3]
                if(not self.__matchIgnoreImapFolder(folderName)):
                    self.__imapFolderList.add(folderName)
                    print 'Include folder '+folderName
        else:
            print 'error, can\'t read folder list:' + repr(folders)
            
    #check if the imap folder should be ignored
    def __matchIgnoreImapFolder(self,imapFolder):
        try:
            if (self.__config.newFolder!=None and imapFolder==self.__config.newFolder):
                return True
            for pattern in self.__ignoreImapFolders:
                if re.match(pattern, imapFolder,re.I):
                    return True
            return False
        except:
            print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Exception during patter match, pattern:'+repr(pattern)+' email:'+repr(imapFolder)
            return True
    #read imap ignore list from *.ign file
    def __readImapIgnoreList(self):
        f = open(self.__config.configFilename+'.ign', 'r')
        self.__ignoreImapFolders = []
        if self.__config.prefix!=None:
                self.__ignoreImapFolders.append((self.__config.prefix+'$').replace('.', '\.'))
        for line in f:
            if self.__config.prefix!=None:
                self.__ignoreImapFolders.append((self.__config.prefix+self.__config.imapDelimiter).replace('.', '\.') +line.strip()+'$')
            else:
                self.__ignoreImapFolders.append(line.strip()+'$')

    # create imap folder from location based on current config and imap delimiter
    def __getImapFolder(self,location):
        if self.__config.prefix!=None:
            return self.__config.prefix+self.__config.imapDelimiter +location.replace('/',self.__config.imapDelimiter)
        else:
            return location.replace('/',self.__config.imapDelimiter)
    
    
    
    # find imap folder for email based on filters
    def findImapFolder(self, email):
        for filter in self.__filters:
            if filter.match(email):
                return filter.getLocation()
        else:
            return None        
            
    def generateFilters(self,imap):
        self.__readImapIgnoreList()
        print time.strftime('%H:%M:%S')+' generate folder list'
        self.__generateImapFolderList(imap)
        print time.strftime('%H:%M:%S')+' generating runtime filters'
        self.__iterateImapFolders(imap)
    

    
    def loadFilters(self,imap,file):
        f = open(file, 'r')
        location = None
        flags=None
        for line in f:
            stripLine = line.strip()
            #skip empty lines
            if(len(stripLine) > 0):
                #if new folder
                if(stripLine[0]=='[' and stripLine[-1]==']'):
                    flagsIndex=stripLine.find('|')
                    #if there are flags
                    if(flagsIndex!=-1):
                        flags=stripLine[flagsIndex+1:-1]
                        location=self.__getImapFolder(stripLine[1:flagsIndex])
                    else:
                        location=self.__getImapFolder(stripLine[1:-1])
                    if( not (location.endswith(FILTER_FOLDER) or location.endswith(FILTER_FOLDER+self.__config.imapDelimiter+DOMAIN_FOLDER)) ):
                        print 'bad folder '+stripLine+', must end with \"'+FILTER_FOLDER+'\" or \"'+DOMAIN_FOLDER+'\"'
                        raise
                    data=imap.select(location)
                    if data[0] != 'OK':
                        print 'error selection folder '+stripLine+' '+repr(data)
                        raise
                #if email pattern
                else:    
                    #if no folder defined jet
                    if(location == None):
                        print 'bad folder format in '+file+', no folder found'
                        raise
                    if not re.match(EMAIL_PATTERN, stripLine,re.I):
                        print 'bad e-mail '+stripLine
                        continue
                    if location.endswith(FILTER_FOLDER+self.__config.imapDelimiter+DOMAIN_FOLDER):
                        data = imap.search(None, '(FROM @'+stripLine.partition('@')[2]+')')
                    else:
                        data = imap.search(None, '(FROM '+stripLine+')')
                    if data[0] == 'OK':
                        if len(string.split(data[1][0]))==0:
                            message= 'From:'+stripLine+'\nTo:FILTER'
                            result=imap.append(location,'\\Seen',None,message)
                            if(result[0] != 'OK'):
                                print  'can\'t create filter message, error:' + repr(result)
                            else:
                                print  'created filter ' + stripLine+' in '+location
                        else:
                            print "Filter "+stripLine+" in folder "+location+" already exists"

    def saveFilters(self,imap,file):
        self.__saveFilters=True
        self.generateFilters(imap)
        f = open(file, 'w')
        for folder in self.__filters:
            f.write('['+folder.getLocation()+']\n')
            for pattern in folder.getPatterns():
                f.write(pattern+'\n')
            f.write('\n')
        f.close()

