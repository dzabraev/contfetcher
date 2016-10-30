# coding=utf8
import os
import ast
import sys

communication_verbose=0

def commlog(msg):
  sys.stdout.write(msg)

def recv_bytes(fd,n):
  b=''
  while n>0:
    b1=os.read(fd,n)
    n-=len(b1)
    b+=b1
  return b

def send_bytes(fd,b):
  n=len(b)
  while n>0:
    n1=os.write(fd,b)
    n-=n1
    b=b[n1:]

def get_msglen(fd):
  b=''
  while True:
    ch=os.read(fd,1)
    if ch==';':
      return int(b)
    else:
      b+=ch

def literal_recv(fd):
  n=get_msglen(fd)
  b=recv_bytes(fd,n)
  s=b.decode('utf8')
  commlog('recv: {}\n'.format(s))
  return ast.literal_eval(s)

def literal_send(fd,literal):
  b=str(literal).encode('utf8')
  n=str(len(b))
  data=n+';'+b
  commlog('send: {}\n'.format(data))
  send_bytes(fd,data)