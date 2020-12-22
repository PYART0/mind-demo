# mind-demo

运行的demo方式： python3 demo.py

一共5个测试用例，分别测试三类API：
1 内置api
2 标准库api
3 mindspore api
4 mindspore api
5 项目自定义api

注意， get_dataflow.py中原来使用的srilm-1.7.2/lm/bin/i686-m64/ngram 为了方便替换成了ngram，将srilm-1.7.2/lm/bin/i686-m64/ 加入了全局变量:
export PATH=$PATH:{path}/srilm-1.7.2/bin/i686-m64
