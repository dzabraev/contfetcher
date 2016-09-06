import sys
import os

def ban(ipfile):
  f=open(ipfile)
  for ip in f.readlines():
    if len(ip) > 0 and ip[-1]=='\n':
      ip=ip[:-1]
    cmd='iptables -A OUTPUT -d {ip} -j DROP'.format(ip=ip)
    print cmd
    os.system(cmd)
  f.close()


if __name__ == "__main__":
  if len(sys.argv)<2:
    print 'usage: badip.txt'
    sys.exit(0)
  ban(sys.argv[1])