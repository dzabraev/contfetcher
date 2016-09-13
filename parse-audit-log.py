import sys
import socket


def usage():
  s='''\
  1. RUN FIREFOX
  2. sudo auditctl -a exit,always -F arch=b64 -S connect -k MYCONNECT -F pid=PID
  3. sudo ausearch -i > /tmp/aui
  4. parse-audit-log.py firefox_PID /tmp/aui
  AFTER this delete logging!
  1. sudo auditctl -d exit,always -F arch=b64 -S connect -k MYCONNECT -F pid=PID
  '''
  print s

# http://serverfault.com/questions/352259/finding-short-lived-tcp-connections-owner-process

def parseAuditLog(fname,**kwargs):
  #parse ausearch -i output
  pid=kwargs.get('pid')
  exe=kwargs.get('exe')
  addrs=[]
  f=open(fname)
  lines=f.read().split('\n')
  bu=[]
  cb=[]
  for line in lines:
    if line=='----':
      if len(cb)>0:
        bu.append(cb)
        cb=[]
    else:
      cb.append(line)
      

  for b in bu:
    if len(b)!=2:
      continue
    l0=b[0].split(' ') #type=SOCKADDR
    l1=b[1].split(' ') #type=SYSCALL
    if 'saddr=inet' in l0:
      if (pid and 'pid={}'.format(pid) in l1) or (exe and 'exe={}'.format(exe) in l1):
        host=None
        port=None
        for field in l0:
          if field[0:4]=='host':
            host=field.split(':')[1]
          if field[0:4]=='serv':
            port=field.split(':')[1]
        addrs.append( (host,int(port)) )
  addrs_uniq=list(set(addrs))
  addrs2=[]
  for ip,port in addrs_uniq:
    try:
      sys.stderr.write('\rprocessing {ip}                     '.format(ip=ip))
      d={'ip':ip,'port':port,'hostname':socket.gethostbyaddr(ip)[0]}
    except socket.herror:
      d={'ip':ip,'port':port,'hostname':None}
    n=0
    for ip2,host2 in addrs:
      if ip==ip2:
        n+=1
    d['n']=n
    addrs2.append(d)
  addrs2.sort( lambda d1,d2: d2['n']-d1['n'])
  for d in addrs2:
    print d['n'] ,d['ip'], d['hostname'], d['port']
  sys.stderr.write('\n')

#parseAuditLog("auditi.log",9420)
if __name__ == "__main__":
  if len(sys.argv)!=3:
    usage()
  exe=sys.argv[1]
  logfile=sys.argv[2]
  parseAuditLog(logfile,exe=exe)
