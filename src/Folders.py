#!/usr/bin/python
'''
Created on May 25, 2011

@author: Alexander Winterwald
'''
import glob
import re
import imaplib, rfc822


class AbstractFolder:
    def match(self, email):
        raise NotImplementedError
    def getLocation(self):
        raise NotImplementedError
    def getFlags(self):
        raise NotImplementedError
    def getPatterns(self):
        raise NotImplementedError
    

class GeneratedFolder(AbstractFolder): #contains list of patterns and folder location

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
    

class Folder(AbstractFolder): #contains list of patterns and folder location

    def __init__(self, location, patterns,flags):
        self.__location=location
        self.__patterns = patterns
        self.__flags=flags
    def match(self, email):
        for pattern in self.__patterns:
            #an exception can be thrown hire
            try:
                if re.match(pattern, email,re.I):
                    return True
            except:
                print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Exception during patter match, pattern:'+repr(pattern)+' email:'+repr(email)
        else:
            return False
    def getLocation(self):
        return self.__location
    def getFlags(self):
        return self.__flags


class FolderList:
    '''
    classdocs
    '''


    def __init__(self,config):
        '''
        Constructor
        '''
        self.__folders=[]
        self.__config=config
    
    def append(self,folder):
            self.__folders.append(folder)
    def findFolder(self, email):
        for folder in self.__folders:
            if folder.match(email):
                return folder
        else:
            return None

    def getFolders(self):
        return self.__folders
        


'''
    def __getFolderPath(self,folderLocation):
        if self.__config.prefix!=None:
            return self.__config.prefix+self.__config.imapDelimiter +folderLocation.replace('/',self.__config.imapDelimiter)
        else:
            return folderLocation.replace('/',self.__config.imapDelimiter)
        
    def readFolders(self,imap):
        for file in glob.glob('*.fld'):
            f = open(file, 'r')
            patterns = []
            location = None
            flags=None

            for line in f:
                stripLine = line.strip()
                #skip empty lines
                if(len(stripLine) > 0):
                    #if new folder
                    if(stripLine[0]=='[' and stripLine[-1]==']'):
                        #if there was a folder before save it
                        if(location != None):
                            folder = Folder(location,patterns,flags)
                            self.__folders.append(folder)
                        patterns = []
                        flagsIndex=stripLine.find('|')
                        #if there are flags
                        if(flagsIndex!=-1):
                            flags=stripLine[flagsIndex+1:-1]
                            location=stripLine[1:flagsIndex]
                        else:
                            location=stripLine[1:-1]
                    #if email pattern
                    else:    
                        #if no folder defined jet
                        if(location == None):
                            print 'bad folder format in '+file+', no folder found'
                            raise
                        if(stripLine[0] == '@' or stripLine.find('@') == -1):
                            patterns.append('.*' + stripLine.replace('.', '\.')+'$')
                        else:
                            patterns.append(stripLine.replace('.', '\.')+'$')
            #save last folder in file
            if(location != None):
                folder = Folder(self.__getFolderPath(location),patterns,flags)
                self.__folders.append(folder)
'''                
