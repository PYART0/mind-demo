import os

rootpath='/home/xincheng/demo/testdata/model_zoo/official/cv'
dirs=os.listdir(rootpath)
sps=os.listdir('testudb/')
print(sps)

for d in dirs:
	proj=rootpath+'/'+d
	if d+'.udb' in sps:
		continue
	outputdir='testudb/'+d+'.udb'
	os.system('und create -db '+outputdir+' -languages python add '+proj+' analyze -all')
	
