#!/usr/bin/python

import marionette
import time
import sys
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
#import pygraphviz
import re
import os
import time
import traceback


PUSH_BUTTON_AWAY=-1
PUSH_BUTTON_OK=0
SUIT_BUTTON_NOT_EXISTS=-1
GRAPH_IRRELEVANT=-2
TRAVERSE_OK=0


def log(msg,**kwargs):
  f=sys.stdout
  needClose=False
  if 'file' in kwargs:
    f=kwargs['file']
  elif 'fname' in kwargs:
    f=open(fname,'a')
    needClose=True
  f.write(msg)
  if needClose:
    f.close()

def bfSearch(G,rootIdx,f):
  queue=[ (rootIdx,[]) ]
  for idx in G.nodes():
    G.node[idx]['mark']=False
  while len(queue)>0:
    idx,path=queue.pop(0)
    if f(G.node[idx]):
      return (idx,path)
    edges=G.edges(idx)
    for a,b in edges:
      if (b not in queue) and (not G.node[b]['mark']):
        bid=G[a][b]['buttonId'][0]
        G.node[b]['mark']=True
        queue.append( (b,path+[bid]) )
  return (-1,[])

def get_bid(node,bad_bids):
  for bid in node['ids']:
    if bid not in bad_bids:
      return bid
  return SUIT_BUTTON_NOT_EXISTS


def printGraph(G,fname='/tmp/graph',**kwargs):
  with open(fname+'.dot','wb') as f:
    f.write('digraph buttonsTree {\n')
    for a in G.nodes():
      h=G.node[a]['h']
      label="id={idx}\\nhashPage={hashPage}\\nnhref={nhref}\\nbuttons={buttons}".format(
        idx=a,
        hashPage=h[0],
        nhref=h[1],
        buttons=h[2]
      )
      label=re.sub('\[','\[',label)
      label=re.sub('\]','\]',label)
      f.write('{node} [label="{label}"];\n'.format(node=a,label=label))
    for (a,b) in G.edges():
      edgeAttrib=G[a][b]
      label='{}'.format(edgeAttrib['buttonId'])
      label=re.sub('\[','\[',label)
      label=re.sub('\]','\]',label)
      f.write('{a} -> {b} [label="{label}"];\n'.format(a=a,b=b,label=label) )
    
    #write legend
    if 'buttons' in kwargs:
      buttons=kwargs['buttons']
      f.write('  { rank = sink;\n')
      f.write('    Legend [shape=none, margin=0, label=<\n')
      f.write('    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">\n')
      for bid in buttons:
        text=buttons[bid]
        line=u'      <TR><TD>{bid}</TD><TD>"{text}"</TD></TR>\n'.format(bid=bid,text=text)
        f.write(line.encode("UTF-8"))
      f.write('  </TABLE>\n')
      f.write('  >]\n')
      f.write('  }\n')
    
    f.write('}\n')
  os.system('dot -Tpng {}.dot -o {}.png'.format(fname,fname))
  print G.nodes()
  print G.edges()


def cleanSubgraph(G,rootIdx,nodeIdx):
  for idx in G.nodes():
    G.node[idx]['mark']=False
  G.remove_node(nodeIdx)
  queue=[rootIdx]
  while len(queue)>0:
    idx=queue.pop(0)
    G.node[idx]['mark']=True
    edges=G.edges(idx)
    for _,b in edges:
      if (b not in queue) and (not G.node[b]['mark']):
        queue.append(b)
  for idx in G.nodes():
    if G.node[idx]['mark']==False:
      G.remove_node(idx)

  
  


class ButtonsGraph:
  def __init__(self,pageUrl):
    client = marionette.Marionette(host='localhost', port=2829)
    client.start_session()
    self.lastPushedButtonId=0
    self.G=nx.DiGraph()
    self.nodeCnt=0
    self.rootIdx=1
    self.client=client
    self.currentNode=None
    self.buttonsDescr={} #tuples (buttonId,text)
    self.loadPage()
    self.pageUrl=self.getCurLoc()
    self.away_buttons=[]
    client.set_context(client.CONTEXT_CHROME)
    client.import_script('js/cf.js')
    #if client.execute_script('return gBrowser.cfPage===undefined;'):
    res=client.execute_script('window.cfPage= new ContfetcherPage(gBrowser.contentDocument);')
    self.addNode(0)
  def updateButtonsDescr(self):
    buttonsDescr=self.buttonsDescr
    client=self.client
    bDescr=client.execute_script('return getButtonsDescr();')
    for d in bDescr:
      bid=d[0]
      text=d[1]
      if bid not in buttonsDescr:
        buttonsDescr[bid]=text
  def loadPage(self,**kwargs):
    url=kwargs.get('url')
    ntry_ajax=kwargs.get('ntry_ajax',1000)
    try_ajax_timeout=kwargs.get('try_ajax_timeout',1.5)
    client=self.client
    client.set_context("content")
    if url:
      sys.stdout.write('loading {}...'.format(url));sys.stdout.flush()
      client.navigate(url)
    else:
      sys.stdout.write('refresh...'.format(url));sys.stdout.flush()
      client.refresh()
    ok=False
    for n in range(ntry_ajax):
      sys.stdout.write('|');sys.stdout.flush()
      try:
        client.find_element('id','contfetcherAjaxCurryd')
        ok=True
        break
      except:
        time.sleep(try_ajax_timeout)
        continue
    if not ok:
      raise Exception
    sys.stdout.write('...ok\n');sys.stdout.flush()
  def evalHashPage(self):
    self.client.set_context(self.client.CONTEXT_CHROME)
    hashPage=self.client.execute_script('return hashPage(gBrowser.contentDocument);')
    hashPage[2]=[int(h) for h in hashPage[2]]
    return hashPage
  def addNode(self,buttonId):
    G=self.G
    hashPage=self.evalHashPage()
    self.updateButtonsDescr()
    idxs=self.G.nodes()
    for idx in idxs:
      #print self.G.node[idx]
      if self.G.node[idx]['h']==hashPage:
        if G.has_edge(self.currentNode,idx):
          G[self.currentNode][idx]['buttonId'].append(buttonId)
        else:
          self.G.add_edge(self.currentNode,idx,buttonId=[buttonId])
          self.currentNode=idx
        print 'new context equal old context(nodeIdx={} buttonId={})'.format(idx,buttonId)
        return
    ids=self.client.execute_script('return getIdActiveElements(gBrowser.contentDocument);')#TODO this exists in hashPage
    ids=[int(b) for b in ids]
    print ids
    self.G.add_node(self.nodeCnt+1,h=hashPage,ids=ids,parButtonId=buttonId)
    if(self.nodeCnt>0):
      self.G.add_edge(self.nodeCnt,self.nodeCnt+1,buttonId=[buttonId])
    self.nodeCnt+=1
    self.currentNode=self.nodeCnt
    print 'added new node id={} buttonId={}'.format(self.nodeCnt,buttonId)
  def gotoRoot(self):
    G=self.G
    client=self.client
    self.loadPage(url=self.pageUrl)
    h1=G.node[self.rootIdx]['h']
    h2=self.evalHashPage()
    if h1 != h2:
      #graph unactual
      log('can\'t goto root node, GRAPH_IRRELEVANT\nh_old={}\nh_new={}\n'.format(h1,h2))
      return GRAPH_IRRELEVANT
    else:
      log('success goto root\n')
    self.currentNode=self.rootIdx
    client.set_context('chrome')
    client.execute_script('window.cfPage.enumerateElements(0,0);')
  def followPath(self,path):
    ''' return:
       0: successfully goto path
      -1: path not is nonactual
      -2: whole graph non actual
    '''
    G=self.G
    client = self.client
    if self.gotoRoot()==GRAPH_IRRELEVANT:
      return GRAPH_IRRELEVANT
    for bId in path:
      self.pushButtonOnly(bId)
      found=False
      for a,b in G.edges(self.currentNode):
        if bId in G[a][b]['buttonId']:
          self.currentNode=b
          found=True
          break
      if not Found:
        log('followPath: edge with {bId} not found, currentNode={idx}'.format(bId=bId,idx=idx))
        raise Exception
      h=self.client.execute_script('return hashPage(gBrowser.contentDocument);')
      tmph=G.node[tmpNodeIdx]
      if h!=tmph:
        #subgraph is nonactual
        cleanSubgraph(G,self.rootIdx,self.currentNode)
        return -1
    return 0

  def getButtonId(self):
    G=self.G
    client=self.client
    rootIdx=1
    fo_ret=-1
    idx=self.currentNode
    cNode=G.node[idx]
    if len(cNode['ids'])>0:
      bid=cNode['ids'][0]
      log('exist unpushed button({bid}) in current node({cnode})\n'.format(bid=bid,cnode=idx))
      return bid
    while fo_ret==-1:
      log('search unpushed button...')
      bf_ret,path=bfSearch(G,rootIdx, lambda node: get_bid(node,self.away_buttons)!=SUIT_BUTTON_NOT_EXISTS )
      if bf_ret==-1:
        #not one node with unpushed button
        log('not exists\n')
        return bf_ret
      else:
        log('found; path={}\n'.format(path) )
        fo_ret=self.followPath(path)
        if fo_ret==0:
          #successfullt goto throw path
          log('success following throw path')
          return get_bid( G.node[self.currentNode], self.away_buttons )
        elif fo_ret==-2:
          log('whole graph unactual')
          return -2
        else:
          #can't goto throw path; Seems tobe the path of graph
          #is nonactual. Try again.
          log('try again follow path')
          continue
    return -1 # Node with unpushed button not found
  def getCurLoc(self):
    client=self.client
    client.set_context("content")
    href=client.execute_script('return window.location.href;')
    client.set_context("chrome")
    return href
  def pushButtonOnly(self,cf_id):
    client=self.client
    href=self.pageUrl
    res=client.execute_script('return window.cfPage.pushButton({});'.format(cf_id))
    while True:
      href1=self.getCurLoc()
      if href != href1:
        #away from page
        log('detect away from page, cf_id={}\n'.format(cf_id))
        return PUSH_BUTTON_AWAY
      print 'check push button'
      res=client.execute_script('return window.cfPage.checkButtonPushed();')
      if res:
        print 'PUSH(id={}): ok'.format(cf_id)
        client.execute_script('window.cfPage.enumerateElements(); return 1;')
        break
    return PUSH_BUTTON_OK
  def pushButton(self,cf_id=None):
    client=self.client
    G=self.G
    if cf_id==None:
      cf_id=self.getButtonId()
    else:
      buttons=self.G.node[self.currentNode]['ids']
      if cf_id not in buttons:
        print 'cf_id={} not exists'.format(cf_id)
        raise Exception
      self.G.node[self.currentNode]['ids']=[b for b in buttons if b!=cf_id]
    res=self.pushButtonOnly(cf_id)
    if res==PUSH_BUTTON_AWAY:
      if self.gotoRoot()==GRAPH_IRRELEVANT:
        return GRAPH_IRRELEVANT
      self.away_buttons.append(cf_id)
    self.addNode(cf_id)
    return PUSH_BUTTON_OK
  def printGraph(self,**kwargs):
    printGraph(self.G,buttons=self.buttonsDescr,**kwargs)
  def traversePage(self):
    fname='dump-graph'
    try:
      for _ in range(100):
        bid=self.getButtonId()
        res=self.pushButton(bid)
        if res==GRAPH_IRRELEVANT:
          return GRAPH_IRRELEVANT
    except Exception as ex:
      log('traverse failed, produce {fname}'.format(fname=fname) )
      traceback.print_exc()
      self.printGraph(fname=fname)
    return TRAVERSE_OK


def action2():
  #client.execute_script('jQuery.ajax=function() {window.alert(\'test\');}')
  g=ButtonsGraph('http://www.mk.ru/news')
  for i in range(3):
    log('traverse attempt {}\n'.format(i))
    res=g.traversePage()
    if res==TRAVERSE_OK:
      log('TRAVERSE_OK\n')
      break
  g.printGraph()
  #g.pushButton(5)
  #g.pushButton(10)
  #g.pushButton(4)
  #g.pushButton(5)
  #g.printGraph()
  
  #print ret
#  for xp in ret:
#    print xp


if __name__ == "__main__":
  action2()