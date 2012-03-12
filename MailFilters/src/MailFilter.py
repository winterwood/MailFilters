#!/usr/bin/python

'''
Created on Feb 28, 2011

@author: Alexander Winterwald

'''
import imaplib, rfc822
import string
from datetime import datetime
import pickle
import os
import sys

from Config import Config
from Folders import FolderList
from Folders import Folder
from FilterGenerator import FilterGenerator
from FilterGenerator import msg
import time
import getopt	


class SyncDate: #syncdate used to indicate a date of synchronisation
	def __init__(self, syncDate):
		self.syncDate = syncDate
		
class MailFilter:
	
	def __init__(self, config):
		self.__config=config
		self.__folders = []
		self.__errors= []
		self.__moved= 0
		self.__syncDateFilename = ''
	
		self.__newSyncDate = None
	

		self.__syncDateFilename=config.configFilename+'.date'
	
	def getLastSyncDate(self):
		if((not self.__config.reFilter) and os.path.isfile(self.__syncDateFilename)):
			cfg = open(self.__syncDateFilename, 'r')
			lastSyncDate = pickle.load(cfg).syncDate
			cfg.close();
		else:
			lastSyncDate = '01-Jan-1970'
		self.__newSyncDate = SyncDate(datetime.now().strftime('%d-%b-%Y'))    
		return lastSyncDate
		
	def saveNewSyncDate(self):
		if(self.__newSyncDate != None):
			cfg = open(self.__syncDateFilename, 'w')
			pickle.dump(self.__newSyncDate, cfg)
			cfg.close()
			
	def executeRule(self,imap, mId, folder, messagesToDelete):
		
		#if target folder ends with minor suffix then add seen flag
		if self.__config.minorSuffix!=None and folder.endswith(self.__config.minorSuffix):
			print 'setting flag seen'
			result=imap.store(mId, '+FLAGS', '\\Seen')
			if(result[0]!='OK'):
				print 'can\'t add seen flag:' + repr(result[1][0])
				self.__errors.append(repr(result[1][0]))
				return
			
		#copy message to the target folder
		result = imap.copy(mId, folder)
		if(result[0]!='OK'):
			print 'can\'t copy message, error:' + repr(result[1][0])
			self.__errors.append(repr(result[1][0]))
			return
		
		#if target folder doesn't ends with minor suffix copy message to the new folder if the new folder exists
		if self.__config.minorSuffix==None or not folder.endswith(self.__config.minorSuffix):
			if(self.__config.newFolder!=None):
				print 'copying message to the new folder'
				result=imap.copy(mId, self.__config.newFolder)
				if(result[0]!='OK'):
					print 'can\'t copy message to a new folder, error:' + repr(result[1][0])
					self.__errors.append(repr(result[1][0]))
					return
				
		#delete the original message
		messagesToDelete.append(mId)
				
	def processNextEmail(self,imap,filterGenerator,mIds):
		messagesToDelete=[]
		for mId in mIds:
			#an exception can happen hire: FETCH command error: BAD ['Error in IMAP command FETCH: Invalid messageset']
			try:
				fromHeader = imap.fetch(mId, '(BODY.PEEK[HEADER.FIELDS (FROM)])')
			except:
				print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Error fetching email:'+repr(mId)
				continue
			if(fromHeader[0] == 'OK'):
				try:
					msgHeaders = rfc822.Message(msg(fromHeader[1][0][1]), 0)
				except:
					print 'Error reading message '+str(fromHeader)
					continue
				folder = filterGenerator.findImapFolder(msgHeaders.getaddr('from')[1])
				if(folder != None):
					print 'found message from:' + msgHeaders.getaddr('from')[1] + ' matching folder:' + folder
					self.executeRule(imap, mId, folder, messagesToDelete)
					'''
					result = imap.copy(mId, folder)
					if(result[0]!='OK'):
						print 'can\'t copy message, error:' + repr(result[1][0])
						self.__errors.append(repr(result[1][0]))
						
					if(self.__config.newFolder!=None):
						result1=imap.copy(mId, self.__config.newFolder)
						if(result1[0]!='OK'):
							print 'can\'t copy message to a new folder, error:' + repr(result1[1][0])
							self.__errors.append(repr(result1[1][0]))
					if(result[0] == 'OK' and (self.__config.newFolder==None or result1[0]=='OK')):
						messagesToDelete.append(mId)
					'''
				else:
					print 'no folder found for message from:' + msgHeaders.getaddr('from')[1]
			else:
				print 'error: can\'t get address from-header:' + repr(fromHeader)
		for mId in messagesToDelete:
			result=imap.store(mId, '+FLAGS', '\\Deleted')
			if(result[0] != 'OK'):
				print 'can\'t delete messages:'+repr(result)
			else:
				self.__moved=self.__moved+1
		imap.expunge()
		return False
								
	def readEmails(self,imap,filterGenerator):
		lastSyncDate = self.getLastSyncDate()
		imap.select()
		searchStr = '(SINCE ' + lastSyncDate + ')'
		print 'Seach for e-mails:' + searchStr
		showNumberOfMessages=True
		while(True):
			data = imap.search(None, searchStr)
			if data[0] == 'OK':
				mIds = string.split(data[1][0])
				if(showNumberOfMessages):
					print 'found ' + str(len(mIds)) + ' new messages'
					showNumberOfMessages=False
				if(not self.processNextEmail(imap, filterGenerator,mIds)):
					break
			else:
				print 'error, can\'t search for e-mails:' + repr(data)
				break
		self.saveNewSyncDate() 
		print time.strftime('%H:%M:%S')+' moved '+repr(self.__moved)+' messages'
		for error in self.__errors:
			print 'ERROR:'+error

if __name__ == '__main__':
	print 'MailFilter r300'
	if(len(sys.argv)<3):
		print 'MailFilter.py < -R | -F | -L <filter file name> | -S <filter file name> > <config file name>'
	else:
		try:
			opts,args=getopt.getopt(sys.argv[1:],"RFL:S:")
		except getopt.GetoptError, err:
			print str(err)
			print 'MailFilter.py < -R | -F | -L <filter file name> | -S <filter file name> > <config file name>'
			sys.exit(2)
		config=Config(args[0])
				
		if(config.ssl):
			imap = imaplib.IMAP4_SSL(config.server, config.port)
		else:
			imap = imaplib.IMAP4(config.server, config.port)
		imap.login(config.login, config.password)
		config.readImap(imap)
		gf = FilterGenerator(config)
		opt,arv=opts[0]
		if opt in ("-R"):
			print 'ReFiltering e-mails'
			config.reFilter=True
			gf.generateFilters(imap)
			mf = MailFilter(config)
			print time.strftime('%H:%M:%S')+' filter e-mails'
			mf.readEmails(imap,gf)
		if opt in ("-F"):
			print 'Filtering e-mails'
			gf.generateFilters(imap)
			mf = MailFilter(config)
			print time.strftime('%H:%M:%S')+' filter e-mails'
			mf.readEmails(imap,gf)
		if opt in ("-L"):
			print 'Loading filters'
			gf.loadFilters(imap, arv)
		if opt in ("-S"):
			print 'Saving filters'
			gf.saveFilters(imap,arv)
		imap.logout()
		print 'All done!'
		
