#!/usr/bin/python
'''
Created on May 25, 2011

@author: Alexander Winterwald
'''

import ConfigParser
import bz2 
import base64
import imaplib
import string

class Config:
    '''
    classdocs
    '''


    def __init__(self,configName):
        '''
        Constructor
        '''
        config = ConfigParser.ConfigParser()
        config.read(configName)
        self.configFilename=configName.rpartition('.')[0]
        
        #Connection
        self.server = config.get('Connection', 'server')
        self.server = config.get('Connection', 'server')
        self.login = config.get('Connection', 'login')
        self.password = bz2.decompress(base64.b64decode(config.get('Connection', 'password')))
        try:
            self.ssl = config.getboolean('Connection', 'ssl')
        except ConfigParser.NoOptionError:
            self.ssl = False
        try:    
            self.port = config.getint('Connection', 'port')
        except ConfigParser.NoOptionError:
            if(self.ssl):
                self.port = 993
            else:
                self.port = 143
        try:
            self.prefix = config.get('Connection', 'prefix')
        except ConfigParser.NoOptionError:
            self.prefix = None
            
        #Options    
            
        try:
            self.newFolder = config.get('Options', 'newFolder')
        except ConfigParser.NoOptionError:
            self.newFolder = None 
               
        try:
            self.minorSuffix = config.get('Options', 'minorSuffix')
        except ConfigParser.NoOptionError:
            self.minorSuffix = None 
        
            
        self.reFilter=False
    
    def readImap(self,imap):
        imap.select()
        imapFolders=imap.list()
        if imapFolders[0] == 'OK':
            self.imapDelimiter=string.split(imapFolders[1][0],'"')[1]
            if self.prefix!=None:
                self.newFolder=self.prefix+self.imapDelimiter+self.newFolder
        else:
            print 'Error, can\'t read imap folder list:'+repr(imapFolders)
            raise 'Error, can\'t read imap folder list:'+repr(imapFolders)
        

    
        