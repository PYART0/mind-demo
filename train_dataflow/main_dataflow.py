#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 19 21:44:52 2020

@author: xincheng
"""

import os,random,re
import get_dataflow


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


def dealwith(ifile):
	with open(ifile) as f:
		lines=f.read()

	x=get_dataflow.get_current_dataflow(lines,'__all__')
	nx=[]
	for ix in x:
		if '(' in ix and not ')' in ix:
			#print(ix)
			ix=re.sub('\(','-->',ix)
		ix=re.sub('-->',' ',ix)
		nx.append(ix)
		global sx
		sx+=ix+'\n'
	print(ifile)
	print(nx)
	print(len(nx))



root_path='/Users/xincheng/Documents/demo/model_zoo'
file_list = dir_list = []
ret_list=[]
get_file_path(root_path,file_list,dir_list)
sx=''

fno=1
for ifile in ret_list:
	print(fno)
	dealwith(ifile)
	fno+=1

with open('train.txt','w+') as f:
	f.write(sx)
