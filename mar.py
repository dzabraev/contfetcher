#!/usr/bin/python


import marionette
import time
import sys
import networkx as nx
#import matplotlib
#import matplotlib.pyplot as plt
#import pygraphviz
import re
import os
import time
import traceback
import json
import datetime

PATH_IRRELEVANT=-1
PUSH_BUTTON_AWAY=-1
PUSH_BUTTON_OK=0
SUIT_BUTTON_NOT_EXISTS=-1
GRAPH_IRRELEVANT=-2

TRAVERSE_OK=0
TRAVERSE_EXCEPT=-2
TRAVERSE_NOTEND=-3
TRAVERSE_MSG={
  TRAVERSE_OK:'TRAVERSE_OK',
  TRAVERSE_EXCEPT:'TRAVERSE_EXCEPT',
  TRAVERSE_NOTEND:'TRAVERSE_NOTEND'
}
NOT_FOUND=-1
SUCCESS=0

BUTTON_PUSH_OK="BUTTON_PUSH_OK"
BUTTON_LOST="BUTTON_LOST"


STORAGE_NOT_EXISTS=-3
LABEL_NOT_MATCH=-2
FINISHED=0
NOT_FINISHED=-1
ALL_BUTTONS_PUSHED=0


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

def get_bid(node,bad_bids,**kwargs):
  lpb=kwargs.get('lpb')
  predicate=kwargs.get('predicate', lambda cf_id: True)
  if lpb!=None:
    if lpb in node['ids'] and predicate(lpb):
      return lpb
  for bid in node['ids']:
    if (bid not in bad_bids) and predicate(bid):
      return bid
  return SUIT_BUTTON_NOT_EXISTS


def printArray(buttons):
  bts=''
  bts+='['
  l=len(buttons)
  for i in range(l):
    bts+=str(buttons[i])
    if i<l-1:
      bts+=','
      if i%10==0 and i!=0:
        bts+='\\n'
  bts+=']'
  return bts


def printGraph(G,**kwargs):
  awayButtonsAll=kwargs.get('awayButtons',[])
  useless=kwargs.get('useless',[])
  fname=kwargs.get('fname','graph')
  with open(fname+'.dot','wb') as f:
    f.write('digraph buttonsTree {\n')
    for a in G.nodes():
      node=G.node[a]
      h=node['h']
      buttons=h[2]
      awayButtonsNode=[ b for b in buttons if b in awayButtonsAll ]
      bts        =printArray( arr_sub(buttons,awayButtonsNode+useless) )
      awayButtons=printArray( awayButtonsNode )
      useless2    =printArray( [b for b in buttons if b in useless] )
      lostButtons=node.get('lostButtons')
      label="id={idx}\\nhashPage={hashPage}\\n\
              nhref={nhref}\\nbuttons={buttons}\\n\
              awayButtons={awayButtons}\\nuseless={useless}".format(
          idx=a,
          hashPage=h[0],
          nhref=h[1],
          buttons=bts,
          awayButtons=awayButtons,
          useless=useless2,
        )
      if lostButtons:
        label+='\\nlostButtons={lostButtons}'.format(lostButtons=lostButtons)
      label=re.sub('\[','\[',label)
      label=re.sub('\]','\]',label)
      f.write('{node} [label="{label}"];\n'.format(node=a,label=label))
    for (a,b) in G.edges():
      edgeAttrib=G[a][b]
      label='{}'.format( printArray(edgeAttrib['buttonId']) )
      label=re.sub('\[','\[',label)
      label=re.sub('\]','\]',label)
      f.write('{a} -> {b} [label="{label}"];\n'.format(a=a,b=b,label=label) )
    
    #write legend
    if 'buttons' in kwargs and len(kwargs['buttons']):
      buttons=kwargs['buttons']
      #buttons.sort(lambda x,y: x[0]-y[0])
      f.write('  { rank = sink;\n')
      f.write('    Legend [shape=none, margin=0, label=<\n')
      f.write('    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">\n')
      k=buttons.keys()
      k.sort( lambda x,y: int(x)-int(y) )
      for bid in k:
        B=buttons[bid]
        if 'img' in B:
          basedir='cf-graph'
          if not os.path.exists(basedir):
            os.makedirs(basedir)
          filename='{}/button-{}.png'.format(basedir,bid)
          fimg=open(filename,'wb')
          fimg.write(B['img'])
          fimg.close()
          line=u'      <TR><TD>{bid}</TD><TD><IMG src="{filename}" SCALE="False" /></TD></TR>\n'.format(bid=bid,filename=filename)
        else:
          txt=''
          for i in range(len(B['text'])):
            txt+=B['text'][i]
            if i>0 and i%40==0:
              txt+='<br/>'
          line=u'      <TR><TD>{bid}</TD><TD>"{text}"</TD></TR>\n'.format(bid=bid,text=txt)
        f.write(line.encode("UTF-8"))
      f.write('  </TABLE>\n')
      f.write('  >]\n')
      f.write('  }\n')
    
    f.write('}\n')
  os.system('dot -Tpng {}.dot -o {}.png'.format(fname,fname))
  print 'print graph {}.png\n'.format(fname)
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



def arr_sub(A,B):
  #A/B
  return [a for a in A if a not in B]
  


class ButtonsGraph:
  def __init__(self,startPageUrl):
    cacheDir='.cache'
    siteCatalog=self.makeShortName(startPageUrl)
    siteDir='{}/{}'.format(cacheDir,siteCatalog)
    hrefsDir='hrefs/{}'.format(siteCatalog)
    self.hrefs_fname='{}/hrefs.txt'.format(hrefsDir)
    if not os.path.exists(hrefsDir):
      os.makedirs(hrefsDir)
    logpath='log/{}'.format(siteCatalog)
    #pageFileName=re.sub('[:./]','_',startPageUrl)
    pageFileName=('_'.join(startPageUrl.split('/')[2:])).replace('.','-')
    if not os.path.exists(logpath):
      os.makedirs(logpath)
    logfname='{}/{}'.format(logpath,pageFileName)
    self.logfile=open(logfname,'w',0)
    dumpGraphName='{}'
    self.client = marionette.Marionette(host='localhost', port=2829)
    self.log('start session marionette\n')
    self.client.start_session()
    client=self.client
    self.lastPushedButtonId=None
    self.G=nx.DiGraph()
    self.nodeCnt=0
    self.rootIdx=1
    self.currentNode=None
    self.buttonsDescr={} #tuples (buttonId,text)
    self.loadPage(url=startPageUrl)
    self.pageUrl=self.getCurLoc()
    self.away_buttons=[]
    self.label=0
    self.hrefs=[]
    self.stats={}
    self.maxButtonsPush=300
    self.uselessPredicate=lambda cf_id: self.stats[cf_id]['existContext']>0
    #
    #stats = {cf_id:stat}
    #stat = {   'nBlank':x,
    #           'newHrefs':x,
    #           'nPush':x,
    #           'existContext':x}
    #
    self.client.set_context(client.CONTEXT_CHROME)
    self.client.import_script('js/cf.js')
    #if self.execute_script('return gBrowser.cfPage===undefined;'):
    buttonsFname='{}/buttons_{}.json'.format(siteDir,pageFileName)
    if os.path.exists(buttonsFname):
      self.log('read buttons from file "{}"\n'.format(buttonsFname) )
      with open(buttonsFname,'r') as f:
        buttons_json=f.read()
        escaped_buttons_json=buttons_json.decode('utf8').replace('\n','\\n').replace('\\"',"\\\\\"")
        self.log('create cfPage object and import buttons\n')
        self.execute_script(u"window.cfPage = new ContfetcherPage(JSON.parse('{}'));".format(
          escaped_buttons_json))
        BS=json.loads(buttons_json)
        for b in BS:
          if b['away']:
            self.away_buttons.append(  b['cf_params']['cf_id']  )
    else:
      self.log('create cfPage object\n')
      res=self.execute_script("window.cfPage = new ContfetcherPage();")
    self.addNode(0)
    self.initHrefs()
  def __del__(self):
    self.logfile.close()
    self.client.delete_session()
  def log(self,msg,**kwargs):
    f=self.logfile
    needClose=False
    if 'file' in kwargs:
      f=kwargs['file']
    elif 'fname' in kwargs:
      f=open(fname,'a')
      needClose=True
    f.write(msg)
    f.flush()
    if needClose:
      f.close()
  def updateButtonsDescr(self):
    buttonsDescr=self.buttonsDescr
    client=self.client
    bDescr=self.execute_script('return getButtonsDescr();')
    for d in bDescr:
      bid=d[0]
      text=d[1]
      if bid not in buttonsDescr:
        if len(text)>0:
          buttonsDescr[bid]={'text':text}
        else:
          #
          #print 'BID=',bid
          elemXpath=self.execute_script('\
            return getXpathSimple(gBrowser.contentDocument,getElementByCfId(gBrowser.contentDocument,{}))'.format(bid))
          client.set_context('content')
          elem=client.find_element('xpath',elemXpath)
          assert elem!=None
          img=client.screenshot(elem,format='binary')
          client.set_context('chrome')
          buttonsDescr[bid]={'img':img}
  def loadPage(self,**kwargs):
    url=kwargs.get('url')
    ntry_ajax=kwargs.get('ntry_ajax',1000)
    try_ajax_timeout=kwargs.get('try_ajax_timeout',1.5)
    client=self.client
    client.set_context("content")
    if url:
      self.log('loading {}'.format(url));
      self.execute_script('window.location.changeLocation(true)')
      client.navigate(url)
      self.execute_script('window.location.changeLocation(false)')
    else:
      self.log('refresh...'.format(url));sys.stdout.flush()
      self.execute_script('window.location.changeLocation(true)')
      client.refresh()
      self.execute_script('window.location.changeLocation(false)')
    ok=False
    for n in range(ntry_ajax):
      #self.log('.')
      try:
        client.find_element('id','contfetcherAjaxCurryd')
        ok=True
        break
      except:
        time.sleep(try_ajax_timeout)
        continue
    client.set_context("chrome")
    if not ok:
      raise Exception
    #self.log(' ok\n')
  def evalHashPage(self):
    self.client.set_context(self.client.CONTEXT_CHROME)
    hashPage=self.execute_script('return hashPage(gBrowser.contentDocument);')
    hashPage[2]=[int(h) for h in hashPage[2]]
    hashPage[2].sort()
    return hashPage
  def getNodeByHash(self,hval):
    G=self.G
    for idx in G.nodes():
      node=G.node[idx]
      if node['h']==hval:
        return idx
    return NOT_FOUND
  def addNode(self,buttonId):
    G=self.G
    stats=self.stats
    if buttonId not in stats:
      stats[buttonId] = {'nPush':0,'existContext':0,'newHrefs':0,'nBlank':0}
    stat = stats[buttonId]
    stat['nPush']+=1
    hashPage=self.evalHashPage()
    self.log('hashPage={}\n'.format(hashPage))
    self.updateButtonsDescr()
    idxs=self.G.nodes()
    for idx in idxs:
      #print self.G.node[idx]
      if 'h' in  self.G.node[idx] and self.G.node[idx]['h']==hashPage:
        stat['existContext']+=1
        if G.has_edge(self.currentNode,idx):
          G[self.currentNode][idx]['buttonId'].append(buttonId)
        else:
          self.G.add_edge(self.currentNode,idx,buttonId=[buttonId])
        self.currentNode=idx
        self.log('new context equal old context(nodeIdx={} buttonId={})\n'.format(idx,buttonId))
        return
    #ids=self.execute_script('return getIdActiveElements(gBrowser.contentDocument);')#TODO this exists in hashPage
    ids=hashPage[2]
    ids=[int(b) for b in ids]
    for bId in ids:
      if bId not in stats:
        stats[bId]={'nPush':0,'existContext':0,'newHrefs':0, 'nBlank':0}
    self.log('new buttons: {}\n'.format(ids))
    newNodeId=self.nodeCnt+1
    self.nodeCnt+=1
    self.G.add_node(newNodeId,h=hashPage,ids=ids,parButtonId=buttonId)
    if(self.currentNode>0):
      self.G.add_edge(self.currentNode,newNodeId,buttonId=[buttonId])
    self.currentNode=newNodeId
    self.log('added new node id={} buttonId={}\n'.format(self.nodeCnt,buttonId))
  def gotoRoot(self):
    G=self.G
    client=self.client
    self.loadPage(url=self.pageUrl)
    client.set_context('chrome')
    self.log('reenumerating root\n')
    self.execute_script('window.cfPage.enumerateElements(0,0);')
    h1=G.node[self.rootIdx]['h']
    h2=self.evalHashPage()
    if h1 != h2:
      #graph unactual
      self.log('GRAPH_IRRELEVANT\nh_old={}\nh_new={}\n'.format(h1,h2))
    else:
      self.log('success goto root\n')
    self.currentNode=self.rootIdx
    self.updateNode(self.rootIdx,h2)
  def updateNode(self,nodeIdx,new_h):
    G=self.G
    node=G.node[nodeIdx]
    old_h=node['h']
    old_unpushed=node['ids']
    old_all=old_h[2]
    old_pushed=arr_sub(old_all,old_unpushed)
    new_all=new_h[2]
    new_unpushed=arr_sub(new_all,old_pushed)
    node['ids']=new_unpushed
    node['h']=new_h
    drop_ids=arr_sub(old_all,new_all)
    for a,b in G.edges(nodeIdx):
      pushed=G[a][b]['buttonId']
      pushed2=arr_sub(pushed,drop_ids)
      if len(pushed2)==0:
        G.remove_edge(a,b)
      else:
        G[a][b]['buttonId']=pushed2

  def followPath(self,path):
    ''' return:
      SUCCESS: successfully goto path
      PATH_IRRELEVANT: incorrect path
    '''
    G=self.G
    client = self.client
    self.gotoRoot()
    for bId in path:
      parent=self.currentNode
      bts=G.node[self.currentNode]['h'][2]
      if bId not in bts:
        return PATH_IRRELEVANT
      found=False
      for a,b in G.edges(self.currentNode):
        if bId in G[a][b]['buttonId']:
          self.currentNode=b
          found=True
          break
      if not found:
        self.log('followPath: edge with {bId} not found, currentNode={idx}'.format(bId=bId,idx=idx))
        raise Exception
      curIdx=self.currentNode
      node=G.node[curIdx]
      self.pushButtonOnly(bId)
      h_old=node['h']
      h_new=self.evalHashPage()
      if h_new!=h_old:
        self.log('node={} irrelevant\n'.format(self.currentNode))
        self.log('h_new={}\nh_old={}\n'.format(h_new,h_old))
        idx=self.getNodeByHash(h_new)
        if idx==NOT_FOUND:
          #replace node with hash=h_old
          self.log('replace existing node, nodeId={}'.format(curIdx))
          self.updateNode(curIdx,h_new)
        else:
          #exists node with hash=h_new
          #1. remove edge parent--->node_with_h_old
          #2. add edge parent--->node_with_h_new
          self.addNode(bId)
          arr=G[parent][curIdx]['buttonId']
          arr=arr_sub(arr,[bId])
          if len(arr)==0:
            G.remove_edge(parent,curIdx)
          if G.has_edge(parent,idx):
            if bId not in G[parent][idx]['buttonId']:
              G[parent][idx]['buttonId'].append(bId)
          else:
            G.add_edge(parent,idx,buttonId=[idx])
          #self.currentNode=idx
        #cleanSubgraph(G,self.rootIdx,self.currentNode)
    return SUCCESS
  def getButtonId(self,cf_id=None):
    # if cf_id != None, then goto node with
    # unpushed cf_id.
    G=self.G
    client=self.client
    rootIdx=1
    fo_ret=-1
    idx=self.currentNode
    cNode=G.node[idx]
    if cf_id == None:
      bid=get_bid(cNode,self.away_buttons,lpb=self.lastPushedButtonId,
        predicate=lambda cf_id: not self.uselessPredicate(cf_id) )
    else:
      if cf_id in cNode['ids']:
        return cf_id
      else:
        bid=-1
    if bid!=-1:
      self.log('exist unpushed button({bid}) in current node({cnode})\n'.format(bid=bid,cnode=idx))
      return bid
    if cf_id==None:
      searchPred=lambda node: get_bid(node,self.away_buttons,
          predicate=lambda cf_id: not self.uselessPredicate(cf_id) )!=SUIT_BUTTON_NOT_EXISTS 
    else:
      searchPred=lambda node: cf_id in node['ids']
    while fo_ret==-1:
      self.log('search unpushed button...')
      bf_ret,path=bfSearch(G,rootIdx, searchPred )
      if bf_ret==-1:
        #not one node with unpushed button
        self.log('not exists\n')
        return bf_ret
      else:
        self.log('found; path={}\n'.format(path) )
        fo_ret=self.followPath(path)
        if fo_ret==0:
          #successfullt goto throw path
          self.log('success following throw path\n')
          if cf_id == None:
            return get_bid( G.node[self.currentNode], self.away_buttons, lpb=self.lastPushedButtonId)
          else:
            return cf_id
        else:
          #can't goto throw path; Seems tobe the path of graph
          #is nonactual. Try again.
          self.log('try again follow path\n')
          continue
    return -1 # Node with unpushed button not found
  def getCurLoc(self):
    client=self.client
    client.set_context("content")
    href=self.execute_script('return window.location.href;')
    client.set_context("chrome")
    return href
  def pushButtonOnly(self,cf_id,layer=None,**kwargs):
    #if cf_id not in self.stats:
    #  self.stats[cf_id] = {'nPush':0,'existContext':0,'newHrefs':0,'nBlank':0}
    res=self._pushButtonOnly(cf_id,layer,**kwargs)
    stat=self.getHrefs()
    self.stats[cf_id]['newHrefs']=stat['newHrefs']
    if stat['newHrefs']==0:
      self.stats[cf_id]['nBlank']+=1
    else:
      self.stats[cf_id]['nBlank']=0
    return res
  def execute_script(self,script):
    self.log('execute_script: {}\n'.format(script))
    res=self.client.execute_script(script)
    self.log('script return: {}\n'.format(res))
    return res
  def _pushButtonOnly(self,cf_id,layer=None,**kwargs):
    client=self.client
    href=self.pageUrl
    label=self.label
    G=self.G
    href1=self.execute_script('return gBrowser.contentDocument.location.lastChangeLocation')
    if href1 != '' and self.selfHref(href1):
      abs_href1=self.execute_script('return makeAbsPath("{}");'.format(href1))
      self.hrefs.append(abs_href1)
    delay =kwargs.get('delay',1)
    sdelay=kwargs.get('sdelay',5)
    ntry=kwargs.get('ntry',1)
    self.label+=1
    self.lastPushedButtonId=cf_id
    self.log('push cf_id={} node_id={}\n'.format(cf_id,self.currentNode))
    resPush=self.execute_script('return window.cfPage.pushButton({},{});'.format(cf_id,label))
    if resPush==BUTTON_LOST:
      node=self.G.node[self.currentNode]
      if 'lostButtons' in node:
        node['lostButtons'].append(cf_id)
      else:
        node['lostButtons'] = [cf_id]
      return BUTTON_LOST
    else:
      while True:
        #self.log('.')
        res=self.execute_script('return window.cfPage.checkButtonPushed({});'.format(label))
        if res==FINISHED:
          #self.log(' ok\n'.format(cf_id))
          if layer:
            self.execute_script('window.cfPage.enumerateElements({},{});'.format(cf_id,layer))
          else:
            self.execute_script('window.cfPage.enumerateElements({});'.format(cf_id))
          break
        elif res==STORAGE_NOT_EXISTS or res==LABEL_NOT_MATCH:
          raise Exception
          self.log('detect away from page, cf_id={}\n'.format(cf_id))
          self.away_buttons.append(cf_id)
          return PUSH_BUTTON_AWAY
        time.sleep(delay)
    return PUSH_BUTTON_OK
  def _pushButtonOnly_old(self,cf_id,layer=None,**kwargs):
    client=self.client
    href=self.pageUrl
    label=self.label
    G=self.G
    delay =kwargs.get('delay',1)
    sdelay=kwargs.get('sdelay',5)
    ntry=kwargs.get('ntry',1)
    self.label+=1
    self.lastPushedButtonId=cf_id
    self.log('push cf_id={} node_id={} .'.format(cf_id,self.currentNode))
    res=self.execute_script('return window.cfPage.pushButton({},{});'.format(cf_id,label))
    time.sleep(sdelay)
    while True:
      #self.log('.')
      href1=self.getCurLoc()
      if href != href1:
        #away from page
        self.log('detect away from page, cf_id={}\n{h1} ---> {h2}\n'.format(cf_id,h1=href,h2=href1))
        if self.selfHref(href1):
          abs_href1=self.execute_script('return makeAbsPath({});'.format(href1))
          self.hrefs.append(abs_href1)
        self.away_buttons.append(cf_id)
        awayNode=G.node[self.currentNode]
        if 'awayButtons' in awayNode:
          awayNode['awayButtons'].append(cf_id)
        else:
          awayNode['awayButtons']=[cf_id]
        return PUSH_BUTTON_AWAY
      res=self.execute_script('return window.cfPage.checkButtonPushed({});'.format(label))
      if res==FINISHED:
        #self.log(' ok\n'.format(cf_id))
        if layer:
          self.execute_script('window.cfPage.enumerateElements({},{});'.format(cf_id,layer))
        else:
          self.execute_script('window.cfPage.enumerateElements({});'.format(cf_id))
        break
      elif res==STORAGE_NOT_EXISTS or res==LABEL_NOT_MATCH:
        raise Exception
        self.log('detect away from page, cf_id={}\n'.format(cf_id))
        self.away_buttons.append(cf_id)
        return PUSH_BUTTON_AWAY
      time.sleep(delay)
    return PUSH_BUTTON_OK
  def pushButton(self,cf_id=None):
    client=self.client
    G=self.G
    if cf_id==None:
      cf_id=self.getButtonId()
    else:
      buttons=self.G.node[self.currentNode]['ids']
      if cf_id not in buttons:
        self.log('cf_id={} not exists'.format(cf_id))
        raise Exception
      self.G.node[self.currentNode]['ids']=[b for b in buttons if b!=cf_id]
    res=self.pushButtonOnly(cf_id)
    if res==PUSH_BUTTON_AWAY:
      if self.gotoRoot()==GRAPH_IRRELEVANT:
        return GRAPH_IRRELEVANT
    else:
      self.addNode(cf_id)
    return PUSH_BUTTON_OK
  def printGraph(self,**kwargs):
    printGraph(self.G,buttons=self.buttonsDescr,awayButtons=self.away_buttons,useless=self.getUseless() ,**kwargs)
  def traversePage(self):
    d1=datetime.datetime.now()
    self.log('start traverse ({}) {}\n'.format(self.pageUrl,str(d1)))
    res=self._traversePage()
    print ''
    d2=datetime.datetime.now()
    self.log('start traverse ({}) {}\n'.format(self.pageUrl,str(d1)))
    self.log('stop  traverse ({}) {}\n'.format(self.pageUrl,str(d2)))
    self.log('{}\n'.format( str(d2-d1) ))
    self.saveHrefs()
    return res
  def _traversePage(self):
    # return:
    #   TRAVERSE_OK
    #   TRAVERSE_EXCEPT
    #   TRAVERSE_NOTEND
    fname='dump-graph'
    self.getHrefs()
    sys.stdout.write('\n')
    try:
      for buttonNumber in range(self.maxButtonsPush):
        bid=self.getButtonId()
        sys.stdout.write('\rpage:{page} pushedBUttons:{bn}'.format(page=self.pageUrl,bn=buttonNumber))
        sys.stdout.flush()
        if bid in self.away_buttons:
          #simple check
          self.saveHrefs()
          self.log('getButtonId return bid={}, and bid in away_buttons\n'.format(bid))
          raise Exception
        elif bid==NOT_FOUND:
          return (TRAVERSE_OK,self.hrefs)
        res=self.pushButton(bid)
    except Exception as ex:
      self.log('traverse failed, produce {fname}\n'.format(fname=fname) )
      traceback.print_exc(None,self.logfile)
      traceback.print_exc()
      self.printGraph(fname=fname)
      self.saveButtons()
      return (TRAVERSE_EXCEPT,self.hrefs)
    bid=self.getButtonId()
    if bid==NOT_FOUND:
      #all buttons done
      return (TRAVERSE_OK,self.hrefs)
    else:
      return (TRAVERSE_NOTEND,self.hrefs)
  def checkUslessCFID(self,cf_id,stat): #UNIPLEMENTED
    # USEFUL
    # USELESS
    # AWAY
    # NOTDETERMINE
    raise Exception
    rootIdx=self.rootIdx
    G=self.G
    self.followPath([])
    node=G.node[self.currentNode]
    buttons=node['ids']
    stats={}
    while True:
      bid=self.getButtonId(cf_id)
      if bid==cf_id:
        res=self.pushButton(bid)
        if res==PUSH_BUTTON_AWAY:
          return (AWAY,stat)
        else: #PUSH_BUTTON_OK
          stat['npush']+=1
      else:
        stat['nNotDet']+=1
        return (NOTDETERMINE,stat)

  def findUslessButtons(self):
    raise Exception
  def makeShortName(self,url):
    arr=url.split('/')
    s=arr[2].split('.')
    shortName='{}_{}'.format(s[-2],s[-1])
    return shortName
  def saveButtons(self):
    client=self.client
    cacheDir='.cache'
    siteCatalog=self.makeShortName(self.pageUrl)
    siteDir='{}/{}'.format(cacheDir,siteCatalog)
    buttonsFname='{}/buttons_{}.json'.format(siteDir,re.sub('[:./]','_',self.pageUrl))
    new_buttons=self.execute_script('return window.cfPage.buttons;')
    for b in new_buttons:
      cf_id=b['cf_params']['cf_id']
      if cf_id in self.away_buttons:
        b['away']=True
      else:
        b['away']=False
    new_buttons_json=json.dumps(new_buttons, ensure_ascii=False, indent=4).encode('utf8')
    if not os.path.exists(siteDir):
      os.makedirs(siteDir)
    with open(buttonsFname,'wb') as fButtons:
      fButtons.write(new_buttons_json)
    self.log('save buttons to {}\n'.format(buttonsFname))
  def getHrefs(self):
    client=self.client
    hrefs=self.hrefs
    stat={'oldHrefs':0,'newHrefs':0}
    newHrefs=self.execute_script('return getSelfHrefs("all",gBrowser.contentDocument,window.cfPage.layer);')
    for href in newHrefs:
      if href in hrefs:
        stat['oldHrefs']+=1
      else:
        stat['newHrefs']+=1
        hrefs.append(href)
    self.log('hrefs: old={} new={}\n'.format(stat['oldHrefs'],stat['newHrefs']))
    return stat
  def saveHrefs(self):
    hrefs=self.hrefs
    hrefs_fname=self.hrefs_fname
    self.log('save hrefs to {}\n'.format(hrefs_fname))
    with open(hrefs_fname,'wb') as f:
      for href in hrefs:
        f.write(href.encode("UTF-8"))
        if len(href)>0 and href[-1] != '\n':
          f.write('\n')
  def initHrefs(self):
    hrefs=self.hrefs
    hrefs_fname=self.hrefs_fname
    if os.path.exists(hrefs_fname):
      self.log('reading {}...'.format(hrefs_fname))
      with open(hrefs_fname,'rb') as f:
        for href in f.readlines():
          if len(href)==0:
            continue
          if href[-1]=='\n':
            href=href[:-1]
          hrefs.append(href)
      self.log('ok\n')
  def selfHref(self,href):
    pageUrl=self.pageUrl
    s1=pageUrl.split('/')[2].split('.')
    s2=href.split('/')[2].split('.')
    return (s1[-1]==s2[-1]) and (s1[-2]==s2[-2])
  def getUseless(self):
    stats=self.stats
    useless=[]
    for cf_id in stats:
      if self.uselessPredicate(cf_id):
        useless.append( cf_id )
    return useless

def traverse(startHref):
  #name=re.sub('[:./]','_'startHref.split('/')[2:].join('/'))
  nam=startHref.split('/')[2].split('.')
  sname='{}_{}'.format(nam[-2],nam[-1]) #"http://www.mk.ru" ---> "mk_ru"
  hdir='hrefs'
  hrefs_fname='{hdir}/{sname}/hrefs.txt'.format(hdir=hdir,sname=sname)
  phrefs_fname='{hdir}/{sname}/phrefs.txt'.format(hdir=hdir,sname=sname)
  log_fname='log/traverse_{}.log'.format(sname)
  for name in [hrefs_fname,phrefs_fname,log_fname]:
    namedir='/'.join(name.split('.')[:-1])
    if not os.path.exists(namedir):
      os.makedirs( namedir )
  logfile=open(log_fname,'a',0)
  logfname.write('\n\n'+str(datetime.datetime.now()))
  np_hrefs=[] #not processed
  p_hrefs=[]  #processed
  if os.path.exists(phrefs_fname):
    phrefs_file=open(phrefs_fname,'r')
    for phref in phrefs_file.readline():
      p_hrefs.append(phref)
    phrefs_file.close()
  if os.path.exists(hrefs_fname):
    hrefs_file=open(hrefs_fname,'r')
    for href in hrefs_file.readline():
      if href not in p_hrefs:
        np_hrefs.append(href)
    hrefs_file.close()
  if startHref in np_hrefs:
    np_hrefs.remove(startHref)
  np_hrefs.insert(0,startHref)

  phrefs_file=open(phrefs_fname,'a')
  hrefs_file =open( hrefs_fname,'a')

  while len(np_hrefs)>0:
    href=np_hrefs.pop(0)
    sys.stdout.write('traverse {}\n'.format(href))
    g=ButtonsGraph(href)
    status,fetched_hrefs=g.traversePage()
    sys.stdout.write('return status: {}, fetcher hrefs: {}\n'.format(TRAVERSE_MSG[status],len(fetched_hrefs)))
    for fhref in fetched_hrefs:
      if (fhref not in np_hrefs) and (fhref not in p_hrefs):
        hrefs_file.write(fhref+'\n')
        np_hrefs.append(fhref)
    if href not in p_hrefs:
      p_hrefs.push(href)
      phrefs_file.write(href+'\n')

  logfile.close()
  phrefs_file.close()
  hrefs_file.close()
  

def action2():
  #self.execute_script('jQuery.ajax=function() {window.alert(\'test\');}')
  g=ButtonsGraph('http://www.mk.ru/news/')
  graphFname='graph-mkru'
  #g=ButtonsGraph('https://ria.ru/lenta/')
  #graphFname='graph-ria'
  #g=ButtonsGraph('http://www.kommersant.ru/')
  #graphFname='graph-kommersant'
  for i in range(1):
    res=g.traversePage()
    if res==TRAVERSE_OK:
      print 'TRAVERSE_OK\n'
      g.printGraph(fname=graphFname)
      g.saveButtons()
      break
    g.printGraph(fname=graphFname)
    g.saveButtons()
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
  #traverse('http://www.mk.ru/news/')
