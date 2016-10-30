# coding=utf8
import sys
import os

import comm
import cflib

def traverse(fd_r,fd_w,marionette_port):
  print 'traverse started!'
  req=comm.literal_recv(fd_r); print req
  act={ 'action':'cfId_request','features':[("A","Загрузить еще","b-pager__button m-button-more")] }
  comm.literal_send(fd_w,act)
  req=comm.literal_recv(fd_r); print req
  act={'action':'urls', 'data':{'type':'urls','buttonId':1,'urls':[
    'https://ria.ru/world/20161030/1480319963.html',
    'https://ria.ru/economy/20161030/1480320038.html',
  ]}}
  act={ 'action':'done' }
  comm.literal_send(fd_w,act)


  while True:
    print comm.literal_recv(fd_r)
    act={ 'action':'done' }
    comm.literal_send(fd_w,act)



