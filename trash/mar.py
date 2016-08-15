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

class ButtonsGraph:
  def __init__(self,baseurl):
    client = marionette.Marionette(host='localhost', port=2829)
    client.start_session()
    sys.stdout.write('loading {}...'.format(baseurl));sys.stdout.flush()
    #client.navigate(baseurl)
    client.refresh()
    sys.stdout.write('ok\n');sys.stdout.flush()
    client.set_context(client.CONTEXT_CHROME)
    client.import_script('js/cf.js')
    #if client.execute_script('return gBrowser.cfPage===undefined;'):
    res=client.execute_script('gBrowser.cfPage= new ContfetcherPage(gBrowser.contentDocument);')
    self.lastPushedButtonId=0
    self.G=nx.DiGraph()
    self.nodeCnt=0
    self.client=client
    self.currentNode=None;
    self.addNode(0)
  def addNode(self,buttonId):
    G=self.G
    self.client.set_context(self.client.CONTEXT_CHROME)
    hashPage=self.client.execute_script('return hashPage(gBrowser.contentDocument);')
    hashPage[2]=[int(h) for h in hashPage[2]]
    idxs=self.G.nodes()
    for idx in idxs:
      #print self.G.node[idx]
      if self.G.node[idx]['h']==hashPage:
        if G.has_edge(self.currentNode,idx):
          G[self.currentNode][idx].append(buttonId)
        else:
          self.G.add_edge(self.currentNode,idx,buttonId=[buttonId])
          self.currentNode=idx
        print 'new context equal old context(nodeIdx={} buttonId={})'.format(idx,buttonId)
        return
    ids=self.client.execute_script('return getIdActiveElements(gBrowser.contentDocument);')#TODO это есть в hashPage
    ids=[int(b) for b in ids]
    print ids
    self.G.add_node(self.nodeCnt+1,h=hashPage,ids=ids,parButtonId=buttonId)
    if(self.nodeCnt>0):
      self.G.add_edge(self.nodeCnt,self.nodeCnt+1,buttonId=[buttonId])
    self.nodeCnt+=1
    self.currentNode=self.nodeCnt
    print 'added new node id={} buttonId={}'.format(self.nodeCnt,buttonId)
  def cleanSubgraph(self,nodeIdx):
    '''
      Удаляется нода с номером nodeIdx, причем
      если в графе существуют узлы, до которых
      можно добраться только через nodeIdx, то такие
      узлы тоже удаляются
    '''
    raise Exception
  def followPath(self,path):
    ''' return:
       0: успешно перешли по path
      -1: path больше не актуальна
      -2: whole graph non actual
    '''
    G=self.G
    client = self.client
    client.set_context('content')
    client.navigate(self.baseurl)
    client.set_context('chrome')
    self.currentNode=1 #начинаем с корня
    h=client.execute_script('return hashPage(gBrowser.contentDocument);')
    tmph=G.node[self.currentNode]['h']
    if h!=tmph:
      #граф целиком не актуален.
      return -2
    for bId in path:
      self.pushButtonOnly(bId)
      found=False
      for a,b in G.edges(self.currentNode):
        if bId in G[a][b]['buttonId']:
          self.currentNode=b
          found=True
          break
      if !Found :
        log('followPath: edge with {bId} not found, currentNode={idx}'.format(bId=bId,idx=idx))
        raise Exception
      h=self.client.execute_script('return hashPage(gBrowser.contentDocument);')
      tmph=G.node[tmpNodeIdx]
      if h!=tmph:
        #подграф не актуален
        self.cleanSubgraph(self.currentNode)
        return -1
    return 0
  def getButtonId(self):
    G=self.G
    client=self.client
    rootIdx=1
    fo_ret=-1
    idx=self.currentNode
    cNode=G.node[idx]
    if cNode['ids'].length > 0:
      return cNode['ids'].pop()
    while fo_ret==-1:
      bf_ret,path=bfSearch(G,rootIdx, lambda node: node['ids'].length>0 )
      if bf_ret==-1:
        #Нету ни одной вершины с ненажатой кнопкой
        return bf_ret
      else:
        fo_ret=self.followPath(path)
        if fo_ret==0:
          #успешно перешли по path
          return G.node[self.currentNode]['ids'].pop()
        elif fo_ret==-2:
          return -2
        else:
          #не удалось перейти по path; Видимо часть графа
          #стала не актуальной. Повторяем процедуру.
          continue
    return -1 # Не нашли ни одной ноды с ненажатыми кнопками
  def pushButtonOnly(self,cf_id):
    res=client.execute_script('return gBrowser.cfPage.pushButton({});'.format(cf_id))
    while True:
      print 'check push button'
      res=client.execute_script('return gBrowser.cfPage.checkButtonPushed();')
      if res:
        print 'PUSH(id={}): ok'.format(cf_id)
        client.execute_script('gBrowser.cfPage.enumerateElements(); return 1;')
        break
  def pushButton(self,cf_id=None):
    client=self.client
    if cf_id==None:
      cf_id=self.getButtonId()
    else:
      buttons=self.G.node[self.currentNode]['ids']
      if cf_id not in buttons:
        print 'cf_id={} not exists'.format(cf_id)
        raise Exception
      self.G.node[self.currentNode]['ids']=[b for b in buttons if b!=cf_id]
    self.pushButtonOnly(cf_id)
    self.addNode(cf_id)
  def printGraph(self,fname='/tmp/graph'):
    G=self.G
    f = plt.figure()
    nx.draw(G,show_labels=True)
    f.savefig(fname+'.jpeg')
    #nx.drawing.nx_agraph.write_dot(A,fname+'.dot')
    with open(fname+'.dot','w') as f:
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
      f.write('}\n')
    os.system('dot -Tpng {}.dot -o {}.png'.format(fname,fname))
    print G.nodes()
    print G.edges()

def action2():
  #client.execute_script('jQuery.ajax=function() {window.alert(\'test\');}')
  #client.set_context(client.CONTEXT_CONTENT)
  #client.navigate('http://www.mk.ru/news/')
  #client.navigate('https://developer.mozilla.org/en-US/docs/Tools/Page_Inspector/How_to/Examine_event_listeners')
  g=ButtonsGraph('http://www.mk.ru/news')
  g.pushButton(5)
  g.pushButton(8)
  g.pushButton(4)
  g.pushButton(5)
  g.printGraph()
  
  #print ret
#  for xp in ret:
#    print xp


if __name__ == "__main__":
  action2()