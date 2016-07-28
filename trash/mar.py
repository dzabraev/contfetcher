import socket
import marionette
import time
import sys

def send_msg(sock,cnt,cmd,args):
  msg='[0, {cnt}, "{cmd}", {args}]'.format(cnt=cnt,cmd=cmd,args=args)
  msg2='{}:{}'.format(len(msg),msg)
  sock.send(msg2)
  print '<---',msg2
  return cnt+1

def action():
  cnt=1
  sock=socket.socket()
  sock.connect(('',2828))
  print '--->',sock.recv(1024)
  cnt=send_msg(sock,cnt,'newSession','{"sessionId": null, "capabilities": null}')
  print '--->',sock.recv(1024) 

def action2():
  client = marionette.Marionette(host='localhost', port=2829)
#  with open('jquery-3.1.0.js') as f:
#    jq=f.read()
  client.start_session()
#  client.execute_script(jq)
  #client.execute_script('jQuery.ajax=function() {window.alert(\'test\');}')
  #client.set_context(client.CONTEXT_CONTENT)
  #client.navigate('http://ria.ru/lenta')
  #client.navigate('https://developer.mozilla.org/en-US/docs/Tools/Page_Inspector/How_to/Examine_event_listeners')
  client.set_context(client.CONTEXT_CHROME)
  #with open('js/eventListeners.js') as f:
  #  script=f.read()
  #client.import_script('js/cf.js')
  #res=client.execute_script('gBrowser.cfPage= new ContfetcherPage(gBrowser.contentDocument);')
  #res=client.execute_script('return gBrowser.cfPage.pushButton(5);')
  #res=client.execute_script('return gBrowser.cfPage.cnt;')
  client.execute_script('return gBrowser.cfPage.enumerateElements();')
  while True:
    print 'check push button'
    res=client.execute_script('return gBrowser.cfPage.checkButtonPushed();')
    if res:
      client.execute_script('return gBrowser.cfPage.enumerateElements();')
      break
  res=client.execute_script('return gBrowser.cfPage.pushButton(12);')
  print res

  #print ret
#  for xp in ret:
#    print xp


if __name__ == "__main__":
  action2()