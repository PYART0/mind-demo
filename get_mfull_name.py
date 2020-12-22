import os,sys,re,importlib


stdlibs=['string','re','difflib','textwrap','unicodedata','stringprep','readline','rlcompleter',
'struct','codecs','datatime','calendar','collections','collections.abc','heapq','bisect',
'array','weakref','types','copy','pprint','reprlib','enum','numbers','math','cmath',
'decimal','fractions','random','statistics','itertools','functools','operator','pathlib',
'os.path','fileinput','stat','filecmp','tempfile','glob','fnmatch','linecache','shutil',
'pickle','copyreg','shelve','marshal','dbm','sqlite3','zlib','gzip','bz2','lzma','zipfile',
'tarfile','csv','configparser','netrc','xdrlib','plistlib','hashlib','hmac','secrets',
'os','io','time','argparse','getopt','logging','logging.config','logging.handlers',
'getpass','curses','curses.textpad','curses.ascii','curses.panel','platform','errno',
'ctypes','threading','multiprocessing','multiprocessing.shared_memory','concurrent',
'concurrent.futures','subprocess','sched','queue','_thread','_dummy_thread','dummy_threading',
'contextvars','asyncio','socket','ssl','select','selectors','asyncore','asynchat','signal',
'mmap','email','json','mailcap','mailbox','mimetypes','base64','binhex','binascii',
'quopri','uu','html','html.parser','html.entities','xml','webbrowser','xml.etree.ElementTree',
'xml.dom','xml.dom.minidom','xml.dom.pulldom','xml.sax','xml.sax.handler','xml.sax.saxutils',
'xml.sax.xmlreader','xml.parsers.expat','cgi','cgitb','wsgiref','urllib','urllib.request',
'urllib.response','urllib.parse','urllib.error','urllib.robotparser','http','http.client',
'ftplib','poplib','imaplib','nntplib','smtplib','smtpd','telnetlib','uuid','socketserver',
'http.server','http.cookies','http.cookiejar','xmlrpc','xmlrpc.client','xmlrpc.server',
'ipaddress','audioop','aifc','sunau','wave','chunk','colorsys','imghdr','sndhdr','ossaudiodev',
'gettext','locale','turtle','cmd','shlex','tkinter','tkinter.ttk','tkinter.tix','tkinter.scrolledtext',
'typing','pydoc','doctest','unittest','unittest.mock','unittest.mock','test','test.support',
'test.support.script_helper','bdb','faulthandler','pdb','timeit','trace','tracemalloc','distutils',
'ensurepip','venv','zipapp','sys','sysconfig','builtins','__main__','warnings','dataclasses',
'contextlib','abc','atexit','traceback','__future__','gc','inspect','site','code','codeop','zipimport',
'pkgutil','modulefinder','runpy','importlib','ast','symtable','symbol','token','keyword',
'tokenize','tabnanny','pyclbr','py_compile','compileall','dis','pickletools','formatter','msilib',
'msvcrt','winreg','winsound','posix','pwd','spwd','grp','crypt','termios','tty','pty','fcntl','pipes',
'resource','nis','optparse','imp']




def get_file_path(root_path,file_list,dir_list):
	global ret_list
	dir_or_files = os.listdir(root_path)
	for dir_file in dir_or_files:
		dir_file_path = os.path.join(root_path,dir_file)
		if os.path.isdir(dir_file_path):
			dir_list.append(dir_file_path)
			get_file_path(dir_file_path,file_list,dir_list)
		elif dir_file_path.endswith('.py') and not dir_file_path.endswith('tmp.py'):
			#print(dir_file_path)
			ret_list.append(dir_file_path)
			file_list.append(dir_file_path)

       
def GetMiddleStr(content,startStr,endStr):
	startIndex = content.index(startStr)
	if startIndex>=0:
		startIndex += len(startStr)
		endIndex = content.index(endStr)
	return content[startIndex:endIndex]
        

def deal_with_current_module(modulename):

	modulename=modulename.strip()
	current_file=CURRENT_FILE
	layer=0
	for c in modulename:
		if c=='.':
			layer+=1
		else:
			break
	#print(layer)
	ls7=current_file.split('/')
	newdirs=ls7[:(0-layer)]
	newdir=''
	for d in newdirs:
		newdir+=d+'/'
	realdir=newdir
	#print(realdir)
	newdir=newdir+'end'
	rootdir=GetMiddleStr(newdir,root_path+'/','/end')
	if modulename=='.':
		rootmodule=re.sub('/','.',rootdir)
	else:
		rootmodule=re.sub('/','.',rootdir)+'.'+modulename[layer:]
	print("Note!",rootmodule)
	for curapi in proj_modules:
		if curapi==rootmodule or curapi.startswith(rootmodule+'.') or '.'+rootmodule+'.' in curapi:
			print('curapi')



#判断模块名是否属于以下情况：标准库/mindspore/第三方库/当前项目/	
def get_module_funcs(modulename):
	modulename=modulename.strip()
	#print(modulename)
	if modulename.startswith('mindspore.') or modulename == 'mindspore' or modulename.startswith('mindarmour.') or modulename == 'mindarmour':
		print('mindspore')
		return 1
	
	for std in stdlibs:
		if modulename == std:
			print('standlib')
			return 2
	
	for api in typesheds:
		if api.startswith(modulename+'.'):
			print('typeshedlib')
			return 3
	
	for curapi in proj_modules:
		if curapi==modulename or curapi.startswith(modulename+'.') or '.'+modulename+'.' in curapi:
			print('curapi')
			return 4
	
	print('otherlib-3tdlib')
	return 5
	
def get_apis(modulename,no):
	cans=[]
	if no==1:
		for mindapi in mindapis:
			if mindapi.startswith(modulename+'.'):
				#print(mindapi)
				tmp=modulename+'.'
				index=mindapi.find(tmp)+len(tmp)
				#print(index)
				shortapi=mindapi[index:]
				#print(shortapi)
				#can=shortapi.split('.')[0]
				cans.append(shortapi)
				#cans.append(mindapi)
		
	elif no==2:
		try:
			module=importlib.import_module(modulename)
			cans.extend(dir(module))
		except Exception:
			index=modulename.rfind('.')
			modulename1=modulename[:index]
			itname=modulename[index+1:]
			try:
				module=importlib.import_module(modulename1)
				item=getattr(module,itname)
				cans.extend(item)
			except Exception as err:
				print(err)
				return []
	elif no==3:
		for api in typesheds:
			if api.startswith(modulename+'.'):
				#print(api)
				tmp=modulename+'.'
				index=api.find(tmp)+len(tmp)
				#print(index)
				shortapi=api[index:]
				#print(shortapi)
				#can=shortapi.split('.')[0]
				cans.append(shortapi)
	elif no==4:
		for curapi in projapis:
			if curapi==modulename or curapi.startswith(modulename+'.') or '.'+modulename+'.' in curapi:
				cans.append(curapi)
		if len(cans)==0:
			modulename1=modulename.split('.')[-1]
			for curapi in projapis:
				if curapi==modulename1 or curapi.startswith(modulename1+'.') or '.'+modulename1+'.' in curapi:
					cans.append(curapi)
	elif no==5:
		try:
			module=importlib.import_module(modulename)
			cans.extend(dir(module))	
		except Exception:
			if '.' in modulename:
				index=modulename.find('.')
				rootmodule=modulename[:index]
				os.system('pip3 install '+rootmodule)
			else:
				os.system('pip3 install '+modulename)
			try:
				module=importlib.import_module(modulename)
				cans.extend(dir(module))	
			except Exception as err:
				print(err)
		
	cans=list(set(cans))
	print(cans)
	return cans
				

def get_module_methods(file):
	modulemethods=[]
	global all_mapis,alias_maps
	with open(file) as f:
		lines=f.readlines()
	for line in lines:
		line=line.strip()

		if re.match('import [a-zA-Z0-9\.\_\,\s]+$',line) and ' as ' not in line:
			#print(1,line)
			modulename=line.split('import')[-1].strip()
			if ',' not in modulename:
				no=get_module_funcs(modulename)
				x=get_apis(modulename,no)
				all_mapis[modulename]=x
			else:
				ls3=modulename.split(',')

				for j in ls3:
					itemname=j.strip()
					no=get_module_funcs(itemname)
					x=get_apis(itemname,no)
					all_mapis[itemname]=x				
			#print(all_mapis)
		elif re.match('import [a-zA-Z0-9\.\_\,]+ as [a-zA-Z0-9\.\_\,\s]+$',line):
			#print(2,line)
			if ',' not in line:
				modulename=GetMiddleStr(line,'import',' as ').strip()
				alias=line.split(' as ')[-1].strip()
				alias_maps[alias]=modulename
				no=get_module_funcs(modulename)
				x=get_apis(modulename,no)
				if len(x)==0:
					#print('yes!')
					for precan in precans:
						if precan.startswith(alias+'.'):
							#print('2')
							index=len(alias)+1
							tx=precan[index:]
							x.append(tx)
				#print(x)
				all_mapis[alias]=x
			#many combing methods, checked by ','
			else:
				body=line.split('import')[-1].strip()
				mas=body.split(',')

				for ma in mas:
					if ' as ' in ma:
						ls4=ma.split(' as ')
						maname=ls4[0].strip()
						aliasname=ls4[1].strip()
						alias_maps[aliasname]=maname
						no=get_module_funcs(maname)
						x=get_apis(maname,no)
						all_mapis[aliasname]=x
					else:
						maname=ma.strip()					
						no=get_module_funcs(maname)
						x=get_apis(maname,no)
						all_mapis[maname]=x
			#print(alias_maps)
			#print(all_mapis)
		elif re.match('from [a-zA-Z0-9\.\_]+ import [a-zA-Z0-9\_\.\*\,\s]+$',line) and 'as' not in line:
			#print(3,line)
			modulename=GetMiddleStr(line,'from','import').strip()
			itemname=line.split('import')[-1].strip()
			names=[]
			if ',' in itemname:
				ns=itemname.split(',')
				for n in ns:
					names.append(n.strip())
			else:
				names.append(itemname)

			if modulename.startswith('.'):
				#TODO
				deal_with_current_module(modulename)
				continue
			
			for n in names:
				no=get_module_funcs(modulename)
				maname=modulename+'.'+n
				x=get_apis(maname,no)
				if len(x)==0:
					for precan in precans:
						if precan.startswith(n+'.'):
							index=len(n)+1
							tx=precan[index:]
							x.append(tx)
				#print(x)
				all_mapis[n]=x
			#print(all_mapis)	
		elif re.match('from [a-zA-Z0-9\.\_]+ import [a-zA-Z0-9\_\.\*\,]+ as [a-zA-Z0-9\_\.\*\,\s]+$',line):
			#print(4,line)
			modulename=GetMiddleStr(line,'from','import').strip()
			#TODO
			no=get_module_funcs(modulename)
			if modulename.startswith('.'):
				#TODO
				deal_with_current_module(modulename)
				continue
			itemname=line.split('import')[-1]
			#print(modulename,itemname)
			if ',' not in itemname:
				lsx=itemname.split(' as ')
				if len(lsx)<2:
					continue
				itname=lsx[0].strip()
				aliasname=lsx[1].strip()
				maname=modulename+'.'+itname
				alias_maps[aliasname]=maname
				x=get_apis(maname,no)
				if len(x)==0:
					for precan in precans:
						if precan.startswith(aliasname+'.'):
							index=len(aliasname)+1
							tx=precan[index:]
							x.append(tx)
				#print(x)
				all_mapis[aliasname]=x
			else:
				ls5=itemname.split(',')
				for it in ls5:
					if ' as ' not in it:
						itname=it.strip()
						maname=modulename+'.'+it
						x=get_apis(maname,no)
						all_mapis[maname]=x
					else:
						itname=it.split(' as ')[0].strip()
						aliasname=it.split(' as ')[1].strip()
						maname=modulename+'.'+itname
						alias_maps[aliasname]=maname
						x=get_apis(maname,no)
						all_mapis[aliasname]=x

			#print(alias_maps)
			#print(all_mapis)
def dealwith(curfile):
	print('Dealing with:',curfile)
	get_module_methods(curfile)
	
	
	

filePath='/home/xincheng/demo/testdata/model_zoo/official/cv/'
projs=os.listdir(filePath)

for p in projs:

	CURRENT_PROJ=p

		
	root_path = filePath+CURRENT_PROJ
	print('LOAD-PROJ:',root_path)


	file_list = dir_list = []
	ret_list=[]
	get_file_path(root_path,file_list,dir_list)

	#获取当前项目模块
	proj_modules=[]
	proj_mfs={}
	for d in dir_list:
		di = re.sub('\.py','',d)
		di = re.sub(root_path+'/','',di)
		di = re.sub('\/','.',di)
		proj_modules.append(di)
		proj_mfs[di]=d
	#print(proj_modules)
	#print(proj_mfs)

	#获取typesehd
	typesheds=[]
	with open('typeshed.txt') as f:
		lines=f.readlines()
	for line in lines:
		typesheds.append(line.strip())
		
	#获取mindspore,api文档不全，备选以源码def信息代替
	mindapis=[]
	with open('mindspore_api_list.txt') as f:
		mlines=f.readlines()
	for mline in mlines:
		mindapis.append(mline.strip())
		
	
	#获取整个项目api
	projapis=[]
	with open('testJson/'+CURRENT_PROJ+'.json') as f:
		plines=f.readlines()
	for pline in plines:
		projapis.append(pline.strip())
		
	precans=[]
	with open('pre_candidates') as f:
		prlines=f.readlines()
	for prline in prlines:
		precans.append(prline.strip())
		
	

	#======MAIN FUNC ENTRY======
	for ifile in ret_list:
		CURRENT_FILE=ifile
		all_mapis={}
		#记录别名
		alias_maps={}
		dealwith(ifile)
