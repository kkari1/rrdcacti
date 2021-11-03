#!/usr/bin/python
# -*- coding: utf-8 -*-

import rrdtool,time
import datetime
import os, glob
import json
from os.path import isdir

class createRRD :

        def __init__(self) :
                self.weblog_dir = "/web_log/*"
                self.access_log = "access_log"
                self.logstate_file = "/tmp/ace/logstate"
                self.logstate_tmpfile = "/tmp/ace/logstate_tmp"
                self.rrd_dir = "/home/traffic/rrd"
                self.img_dir = "/home/traffic/img"
                self.timestamp = int(time.time())

        #로그파일들의 풀경로를 log_path 에 저장하고 리턴
        def getLogFile(self) :
                list = filter(os.path.isdir, glob.glob(self.weblog_dir))
                log_path = []
                for path in list:
                        fullpath = path + "/" + self.access_log
                        if os.path.isfile(fullpath):
                                log_path.append(fullpath)
                return log_path

        #각 도메인별 rrd파일 생성
        def makeRRDfile(self) :
                log_path = self.getLogFile()
                for data in log_path :
                        domain = data.split('/')[2]
                        filename = self.rrd_dir + "/" + domain + ".rrd"
                        if not os.path.isfile(filename) :
                                rrdtool.create(
                                               filename, '-s' , "60" ,
                                                "DS:IN_TRA:GAUGE:600:0:U",
                                                "DS:OUT_TRA:GAUGE:600:0:U",
                                                "RRA:AVERAGE:0.5:1:4000",
                                                "RRA:AVERAGE:0.5:30:1600",
                                                "RRA:AVERAGE:0.5:120:1600",
                                                "RRA:AVERAGE:0.5:1440:1600",
                                                "RRA:LAST:0.5:1:4000",
                                                "RRA:LAST:0.5:30:1600",
                                                "RRA:LAST:0.5:120:1600",
                                                "RRA:LAST:0.5:1440:1600",
                                                "RRA:MAX:0.5:1:4000",
                                                "RRA:MAX:0.5:30:1600",
                                                "RRA:MAX:0.5:120:1600",
                                                "RRA:MAX:0.5:1440:1600"
                                )

        #00:00 에 logstate 파일 초기화
        def resetLogState(self) :
                logfile = self.getLogFile()
                if os.path.isfile(self.logstate_file) :
                        os.remove(self.logstate_file)

                for access_log in logfile :
                        data = dict()
                        data['log_path'] = access_log
                        data['last_line'] = 0
                        json_data = json.dumps(data)
                        fstate = open(self.logstate_file, 'a')
                        fstate.write(json_data+"\n")
                        fstate.close()

        #access로그에서 도메인, in , out 트래픽량 추출하여 rrd 파일에 업데이트
        def updateTraffic(self) :
                file = open(self.logstate_file, 'r')
                while True :
                        line = file.readline()
                        if not line :
                                break
                        result  = json.loads(line)
                        log_path = result['log_path']
                        last_line = result['last_line']
                        domain = result['log_path'].split('/')[2]
                        if os.path.getsize(log_path) :
                                with open(log_path) as fp :
                                        in_total = 0
                                        out_total = 0
                                        for line_num, line in enumerate(fp) :
                                                tr_total = line.split('\"')[7].split(" ")
                                                #injection 으로 인해 access_log 라인이 split이 안될경우 in,out 0으로 설정
                                                if len(tr_total) < 2 :
                                                        in_tr = 0
                                                        out_tr = 0
                                                elif len(tr_total) == 2 :
                                                        try:
                                                                in_tr = tr_total[0]
                                                                out_tr = tr_total[1]
                                                                in_tr = int(in_tr)
                                                                out_tr = int(out_tr)
                                                        except:
                                                                in_tr = 0
                                                                out_tr = 0
                                                else :
                                                        in_tr = 0
                                                        out_tr = 0
                                                if line_num > last_line :
                                                        in_total = in_total + in_tr
                                                        out_total = out_total + out_tr
                                                line_num += 1
                                        in_total = in_total * 8 / 60
                                        out_total = out_total * 8 / 60
                                        #이 값으로 rrd 업데이트 치고, logstate 라인넘버 업데이트
                                        #print(in_total)
                                        #print(out_total)
                                        #print(line_num-1)
                                        line_num = line_num - 1
                        #웹로그 파일크기 0일경우 0으로 입력
                        else :
                                in_total = 0
                                out_total = 0
                                line_num = 0
                        #logstate_bak 파일 만들어서 여기다가 라인넘버 갱신
                        file2 = open(self.logstate_tmpfile, 'a')
                        data = dict()
                        data['log_path'] = log_path
                        data['last_line'] = line_num
                        json_data = json.dumps(data)
                        file2.write(json_data+"\n")
                        file2.close()
                        #rrd 업데이트 구문 여기다가 쳐야함
                        filename = self.rrd_dir + "/" + domain + ".rrd"
                        filename = str(filename)
                        rrddata = "N:" + str(in_total) + ":" + str(out_total)
                        rrdtool.update(filename,rrddata)
                        #그래프 생성
                        self.makeGraph(str(domain))
                file.close()
                #logstate_bak -> logstate 로 이름바꾸고 기존 logstate 삭제
                if os.path.isfile(self.logstate_tmpfile):
                        os.remove(self.logstate_file)
                        os.rename(self.logstate_tmpfile, self.logstate_file)


        def makeGraph(self, domain) :
                s = 60*60*24
                t = self.timestamp
                start = t - s
                domain = domain
                imgFile = self.img_dir + "/" + domain + "_traffic_daily.png"
                rrdFile = self.rrd_dir + "/" + domain + ".rrd"
                result = rrdtool.graph("%s" %imgFile,
                  "--title", "%s" %domain,
                  "--start", "%s" %start,
                  "--end", "%s" %t,
                  "--interlace",
                  "--imgformat","PNG",
                  "--width=360",
                  "--height=80",
                  "-nTITLE:8:",
                  "-nLEGEND:7",
                  "DEF:ds0=%s:IN_TRA:AVERAGE" %rrdFile,
                  "DEF:ds1=%s:OUT_TRA:AVERAGE" %rrdFile,
                  "CDEF:in=ds0,1,*,-1,/",
                  "CDEF:out=ds1,1,*,1,/",
                  "CDEF:in1=in,-1,*",
                  "AREA:out#800080:Out",
                  "GPRINT:out:MAX:[ MAX %5.2lf%Sbps",
                  "GPRINT:out:AVERAGE:Avg %5.2lf%Sbps",
                  "GPRINT:out:LAST:Cur %5.2lf%Sbps ]\\n",
                  "AREA:in#0022e9:In",
                  "GPRINT:in1:MAX:[ MAX %5.2lf%Sbps",
                  "GPRINT:in1:AVERAGE:Avg %5.2lf%Sbps",
                  "GPRINT:in1:LAST:Cur %5.2lf%Sbps ]\\n"
                )

        def makeIndex(self) :
                imgFiles = self.img_dir + "/*"
                list = filter(os.path.isfile, sorted(glob.glob(imgFiles), key=os.path.getsize , reverse=True))
                indexFile = '/home/traffic/index.html'
                indexBakFile='/home/traffic/index.html_bak'

                f = open(indexBakFile, 'a')
                f.write("<HEAD><META HTTP-EQUIV=Refresh CONTENT=60></HEAD>\n")
                for line in list:
                        line = line.split('/home/traffic/')[1]
                        f.write("<tr><td ><img src=%s></a></td>\n"%line)

                f.close()
                if os.path.isfile(indexFile):
                        os.remove(indexFile)
                        os.rename(indexBakFile, indexFile)


def main() :
        create = createRRD()
        create.makeRRDfile()
        date = datetime.datetime.today()
        if date.hour == 0 and date.minute == 0 :
                create.resetLogState()
                time.sleep(50)
        #create.resetLogState()
        create.updateTraffic()
        create.makeIndex()

if __name__ == '__main__' :
        main()
